"""
Zoom Cloud Recording Transcription Pipeline

This pipeline:
1. Reads recording info from a Google Sheet (with share URLs)
2. Downloads each recording from Zoom
3. Transcribes them using Whisper
4. Stores transcripts in an indexed JSON file

Setup:
    pip install requests gspread oauth2client openai-whisper --break-system-packages
    
    For Google Sheets API:
    - Go to https://console.cloud.google.com/
    - Enable Google Sheets API
    - Create service account credentials
    - Download JSON key file
    - Share your Google Sheet with the service account email
"""

import os
import requests
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
import time

# Optional: Google Sheets integration
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False
    print("⚠️  Google Sheets libraries not installed. Install with: pip install gspread oauth2client")

# Optional: Whisper for transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️  Whisper not installed. Install with: pip install openai-whisper")


class ZoomTranscriptionPipeline:
    def __init__(self, account_id: str, client_id: str, client_secret: str, 
                 user_id: str, google_sheets_creds_path: Optional[str] = None):
        """
        Initialize the pipeline.
        
        Args:
            account_id: Zoom account ID
            client_id: Zoom OAuth app client ID
            client_secret: Zoom OAuth app client secret
            user_id: Zoom user email/ID whose recordings to access
            google_sheets_creds_path: Path to Google service account JSON file
        """
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.access_token = None
        self.base_url = "https://api.zoom.us/v2"
        
        # Google Sheets setup
        self.google_sheets_creds_path = google_sheets_creds_path
        self.gsheet_client = None
        
        # Create directories
        self.recordings_dir = Path("recordings")
        self.transcripts_dir = Path("transcripts")
        self.recordings_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)
        
        # Initialize Whisper model (lazy loading)
        self.whisper_model = None
    
    def get_access_token(self) -> str:
        """Get OAuth access token from Zoom"""
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"
        
        response = requests.post(
            url,
            auth=(self.client_id, self.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            print("✅ Obtained Zoom access token")
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")
    
    def extract_recording_id_from_share_url(self, share_url: str) -> Optional[str]:
        """
        Extract recording identifier from Zoom share URL.
        Example: https://zoom.us/rec/share/abc123... -> abc123...
        """
        try:
            # Parse the URL
            parsed = urlparse(share_url)
            
            # Check if it's a /rec/share/ URL
            if '/rec/share/' in parsed.path:
                # Extract the ID from the path
                parts = parsed.path.split('/rec/share/')
                if len(parts) > 1:
                    recording_id = parts[1].split('/')[0].split('?')[0]
                    return recording_id
            
            # Check for recording ID in query parameters
            query_params = parse_qs(parsed.query)
            if 'recording_id' in query_params:
                return query_params['recording_id'][0]
            
            print(f"⚠️  Could not extract recording ID from URL: {share_url}")
            return None
            
        except Exception as e:
            print(f"⚠️  Error parsing URL: {str(e)}")
            return None
    
    def read_from_google_sheet(self, sheet_url: str, worksheet_name: str = "Sheet1") -> List[Dict]:
        """
        Read recording information from Google Sheet.
        
        Expected columns:
        - Video Name (Column A)
        - Date (Column B)
        - Share URL (Column C)
        - Notes (Column D)
        """
        if not GSHEETS_AVAILABLE:
            raise Exception("Google Sheets libraries not installed")
        
        if not self.google_sheets_creds_path:
            raise Exception("Google Sheets credentials path not provided")
        
        # Authenticate
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            self.google_sheets_creds_path, scope)
        self.gsheet_client = gspread.authorize(creds)
        
        # Open the sheet
        sheet = self.gsheet_client.open_by_url(sheet_url).worksheet(worksheet_name)
        
        # Get all records
        records = sheet.get_all_records()
        
        print(f"✅ Read {len(records)} recordings from Google Sheet")
        return records
    
    def read_from_csv(self, csv_path: str) -> List[Dict]:
        """
        Read recording information from a CSV file.
        
        Expected columns: Video Name, Date, Share URL, Notes
        """
        import csv
        
        recordings = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            recordings = list(reader)
        
        print(f"✅ Read {len(recordings)} recordings from CSV")
        return recordings
    
    def get_recording_download_url(self, share_url: str) -> Optional[Dict]:
        """
        Get the actual download URL for a recording from its share URL.
        This requires some API calls to find the recording.
        """
        if not self.access_token:
            self.get_access_token()
        
        # Extract recording ID from share URL
        recording_id = self.extract_recording_id_from_share_url(share_url)
        
        if not recording_id:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # List all recordings and find the matching one
        url = f"{self.base_url}/users/{self.user_id}/recordings"
        params = {"page_size": 300}
        
        try:
            while True:
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"⚠️  API error: {response.status_code}")
                    return None
                
                data = response.json()
                
                # Search through meetings
                for meeting in data.get("meetings", []):
                    # Check share_url or recording files
                    meeting_share_url = meeting.get("share_url", "")
                    
                    if recording_id in meeting_share_url:
                        # Found the meeting! Get the primary video file
                        for file in meeting.get("recording_files", []):
                            if file.get("file_type") in ["MP4", "M4A"]:
                                return {
                                    "meeting_id": meeting.get("id"),
                                    "meeting_uuid": meeting.get("uuid"),
                                    "topic": meeting.get("topic"),
                                    "start_time": meeting.get("start_time"),
                                    "download_url": file.get("download_url"),
                                    "play_url": file.get("play_url"),
                                    "file_type": file.get("file_type"),
                                    "file_size": file.get("file_size"),
                                    "recording_start": file.get("recording_start"),
                                    "recording_end": file.get("recording_end")
                                }
                
                # Check for next page
                next_page_token = data.get("next_page_token")
                if next_page_token:
                    params["next_page_token"] = next_page_token
                else:
                    break
            
            print(f"⚠️  Could not find recording with ID: {recording_id}")
            return None
            
        except Exception as e:
            print(f"⚠️  Exception: {str(e)}")
            return None
    
    def download_recording(self, download_url: str, output_path: Path) -> bool:
        """Download a recording file"""
        if not self.access_token:
            self.get_access_token()
        
        # Add access token to URL
        if "?" in download_url:
            download_url += f"&access_token={self.access_token}"
        else:
            download_url += f"?access_token={self.access_token}"
        
        try:
            print(f"📥 Downloading recording...")
            response = requests.get(download_url, stream=True)
            
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                with open(output_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end='')
                print(f"\n✅ Downloaded to {output_path}")
                return True
            else:
                print(f"\n⚠️  Download failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"\n⚠️  Download error: {str(e)}")
            return False
    
    def transcribe_audio(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio file using Whisper"""
        if not WHISPER_AVAILABLE:
            print("⚠️  Whisper not available. Install with: pip install openai-whisper")
            return None
        
        try:
            # Load model (lazy loading)
            if self.whisper_model is None:
                print("🔄 Loading Whisper model (this may take a minute)...")
                self.whisper_model = whisper.load_model("base")  # or "small", "medium", "large"
            
            print(f"🎙️  Transcribing {audio_path.name}...")
            result = self.whisper_model.transcribe(str(audio_path))
            
            print("✅ Transcription complete")
            return result["text"]
            
        except Exception as e:
            print(f"⚠️  Transcription error: {str(e)}")
            return None
    
    def process_recordings(self, recordings_input: List[Dict]) -> Dict[str, Dict]:
        """
        Main pipeline: process all recordings.
        
        Args:
            recordings_input: List of dicts with keys: 'Video Name', 'Date', 'Share URL', 'Notes'
        
        Returns:
            Dictionary indexed by a unique ID for each recording
        """
        results = {}
        
        for idx, recording in enumerate(recordings_input):
            video_name = recording.get('Video Name', f'Recording {idx+1}')
            date = recording.get('Date', 'Unknown')
            share_url = recording.get('Share URL', '')
            notes = recording.get('Notes', '')
            
            print(f"\n{'='*60}")
            print(f"Processing: {video_name} ({date})")
            print(f"{'='*60}")
            
            if not share_url:
                print("⚠️  No share URL provided, skipping...")
                continue
            
            # Step 1: Get download URL
            print("Step 1: Fetching recording metadata...")
            metadata = self.get_recording_download_url(share_url)
            
            if not metadata:
                print("❌ Could not find recording")
                results[f"recording_{idx+1}"] = {
                    "video_name": video_name,
                    "date": date,
                    "status": "failed",
                    "error": "Could not find recording"
                }
                continue
            
            # Step 2: Download
            recording_id = f"recording_{idx+1}_{metadata['meeting_id']}"
            file_extension = ".mp4" if metadata['file_type'] == "MP4" else ".m4a"
            local_path = self.recordings_dir / f"{recording_id}{file_extension}"
            
            print("Step 2: Downloading...")
            if not self.download_recording(metadata['download_url'], local_path):
                print("❌ Download failed")
                results[recording_id] = {
                    "video_name": video_name,
                    "date": date,
                    "status": "failed",
                    "error": "Download failed"
                }
                continue
            
            # Step 3: Transcribe
            print("Step 3: Transcribing...")
            transcript = self.transcribe_audio(local_path)
            
            if not transcript:
                print("❌ Transcription failed")
                results[recording_id] = {
                    "video_name": video_name,
                    "date": date,
                    "status": "failed",
                    "error": "Transcription failed",
                    "local_file": str(local_path)
                }
                continue
            
            # Step 4: Store results
            results[recording_id] = {
                "video_name": video_name,
                "date": date,
                "notes": notes,
                "status": "success",
                "meeting_id": metadata['meeting_id'],
                "topic": metadata['topic'],
                "start_time": metadata['start_time'],
                "recording_start": metadata['recording_start'],
                "recording_end": metadata['recording_end'],
                "local_file": str(local_path),
                "transcript": transcript,
                "processed_at": datetime.now().isoformat()
            }
            
            print(f"✅ Successfully processed {video_name}")
        
        return results
    
    def save_results(self, results: Dict[str, Dict], output_path: Path):
        """Save results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {output_path}")


# Example usage
if __name__ == "__main__":
    # Configuration
    ZOOM_ACCOUNT_ID = "your_account_id_here"
    ZOOM_CLIENT_ID = "your_client_id_here"
    ZOOM_CLIENT_SECRET = "your_client_secret_here"
    ZOOM_USER_ID = "your_email@example.com"
    
    # Optional: Google Sheets
    GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
    GOOGLE_CREDS_PATH = "path/to/service-account-key.json"
    
    # Initialize pipeline
    pipeline = ZoomTranscriptionPipeline(
        account_id=ZOOM_ACCOUNT_ID,
        client_id=ZOOM_CLIENT_ID,
        client_secret=ZOOM_CLIENT_SECRET,
        user_id=ZOOM_USER_ID,
        google_sheets_creds_path=GOOGLE_CREDS_PATH
    )
    
    # Option 1: Read from Google Sheets
    # recordings = pipeline.read_from_google_sheet(GOOGLE_SHEET_URL)
    
    # Option 2: Read from CSV
    # recordings = pipeline.read_from_csv("recordings_list.csv")
    
    # Option 3: Manual list
    recordings = [
        {
            "Video Name": "Team Meeting",
            "Date": "2025-11-15",
            "Share URL": "https://zoom.us/rec/share/abc123...",
            "Notes": "Important discussion"
        },
        # Add more recordings here
    ]
    
    # Process all recordings
    results = pipeline.process_recordings(recordings)
    
    # Save results
    output_file = Path("transcripts") / f"transcripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    pipeline.save_results(results, output_file)
    
    print("\n" + "="*60)
    print("Pipeline complete!")
    print(f"Processed {len(results)} recordings")
    print(f"Results saved to: {output_file}")
    print("="*60