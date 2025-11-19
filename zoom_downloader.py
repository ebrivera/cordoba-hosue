"""
Zoom Video Downloader

A focused class for downloading Zoom cloud recordings.
Supports downloading from share URLs or direct meeting IDs.

Important Limitations:
    - Share links and API access are different systems
    - Share links might be from a DIFFERENT Zoom account than the one you're authenticated with
    - The API searches YOUR account's recordings, not all public share links
    - If a recording isn't found via API, the downloader attempts direct web scraping

Setup:
    pip install requests python-dotenv --break-system-packages

    Create a .env file with:
    ZOOM_ACCOUNT_ID=your_account_id
    ZOOM_CLIENT_ID=your_client_id
    ZOOM_CLIENT_SECRET=your_client_secret
    ZOOM_USER_ID=your_email@example.com  # The account that owns the recordings
"""

import os
import requests
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
import time


class ZoomDownloader:
    """Download Zoom cloud recordings from share URLs or meeting IDs"""

    def __init__(self, account_id: str, client_id: str, client_secret: str,
                 user_id: str, output_dir: str = "recordings"):
        """
        Initialize the Zoom downloader.

        Args:
            account_id: Zoom account ID
            client_id: Zoom OAuth app client ID
            client_secret: Zoom OAuth app client secret
            user_id: Zoom user email/ID whose recordings to access
            output_dir: Directory to save downloaded recordings
        """
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.access_token = None
        self.base_url = "https://api.zoom.us/v2"

        # Create output directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        print(f"✅ ZoomDownloader initialized")
        print(f"   Output directory: {self.output_dir.absolute()}")

    def get_access_token(self) -> str:
        """
        Get OAuth access token from Zoom using Server-to-Server OAuth.
        Token is valid for 1 hour.
        """
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"

        try:
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
                error_msg = f"Failed to get access token: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            raise

    def extract_recording_id_from_share_url(self, share_url: str) -> Optional[str]:
        """
        Extract recording identifier from Zoom share URL.

        Examples:
            https://us02web.zoom.us/rec/share/K87Fx1wSLflLf6-jeKItz...
            -> K87Fx1wSLflLf6-jeKItz...

        Args:
            share_url: The Zoom share URL

        Returns:
            The recording ID or None if extraction failed
        """
        try:
            parsed = urlparse(share_url)

            # Check if it's a /rec/share/ URL
            if '/rec/share/' in parsed.path:
                # Extract the ID from the path
                parts = parsed.path.split('/rec/share/')
                if len(parts) > 1:
                    recording_id = parts[1].split('/')[0].split('?')[0]
                    print(f"📝 Extracted recording ID: {recording_id}")
                    return recording_id

            # Check for recording ID in query parameters
            query_params = parse_qs(parsed.query)
            if 'recording_id' in query_params:
                recording_id = query_params['recording_id'][0]
                print(f"📝 Extracted recording ID: {recording_id}")
                return recording_id

            print(f"⚠️  Could not extract recording ID from URL: {share_url}")
            return None

        except Exception as e:
            print(f"❌ Error parsing URL: {str(e)}")
            return None

    def get_recording_metadata(self, share_url: str, debug: bool = True) -> Optional[Dict]:
        """
        Get recording metadata and download URL from a share URL.

        This searches through the user's recordings to find the matching one.

        Args:
            share_url: The Zoom share URL
            debug: If True, print debug information about found recordings

        Returns:
            Dictionary with recording metadata including download_url, or None if not found
        """
        # Ensure we have an access token
        if not self.access_token:
            self.get_access_token()

        # Extract recording ID from share URL
        recording_id = self.extract_recording_id_from_share_url(share_url)

        if not recording_id:
            print("❌ Could not extract recording ID from share URL")
            return None

        # Extract start time from URL to help narrow search
        from datetime import datetime, timedelta
        parsed_url = urlparse(share_url)
        query_params = parse_qs(parsed_url.query)
        start_time_ms = query_params.get('startTime', [None])[0]

        # Determine date range for search
        if start_time_ms:
            start_timestamp = int(start_time_ms) / 1000
            recording_date = datetime.fromtimestamp(start_timestamp)
            # Search from 7 days before to 7 days after the recording
            from_date = (recording_date - timedelta(days=7)).strftime('%Y-%m-%d')
            to_date = (recording_date + timedelta(days=7)).strftime('%Y-%m-%d')
            print(f"📅 Recording date: {recording_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Searching from {from_date} to {to_date}")
        else:
            # Default to last 30 days if no date in URL
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # List recordings with date range
        url = f"{self.base_url}/users/{self.user_id}/recordings"
        params = {
            "page_size": 300,
            "from": from_date,
            "to": to_date
        }

        try:
            print(f"🔍 Searching for recording in user's cloud recordings...")
            page_count = 0
            total_meetings = 0
            found_recordings = []

            while True:
                page_count += 1
                print(f"   Checking page {page_count}...", end='\r')

                response = requests.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    print(f"\n❌ API error: {response.status_code} - {response.text}")
                    return None

                data = response.json()
                meetings = data.get("meetings", [])
                total_meetings += len(meetings)

                # Debug: collect info about found recordings
                if debug and meetings:
                    for m in meetings:
                        found_recordings.append({
                            "topic": m.get("topic", "Unknown"),
                            "start_time": m.get("start_time", "Unknown"),
                            "share_url": m.get("share_url", ""),
                            "uuid": m.get("uuid", "")
                        })

                # Search through meetings
                for meeting in meetings:
                    # Strategy 1: Check if share_url contains our recording ID
                    meeting_share_url = meeting.get("share_url", "")
                    match_found = False

                    if recording_id in meeting_share_url:
                        match_found = True
                        print(f"\n✅ Found matching recording (by share URL)!")

                    # Strategy 2: If we have a timestamp, match by recording start time
                    elif start_time_ms:
                        # Check all recording files in this meeting
                        for file in meeting.get("recording_files", []):
                            file_recording_start = file.get("recording_start", "")
                            if file_recording_start:
                                try:
                                    # Parse the ISO timestamp from API (timezone-aware UTC)
                                    from datetime import timezone
                                    file_time = datetime.fromisoformat(file_recording_start.replace('Z', '+00:00'))
                                    # Make target time also timezone-aware UTC
                                    target_time = datetime.fromtimestamp(int(start_time_ms) / 1000, tz=timezone.utc)

                                    # Allow 5 minute tolerance for timestamp matching
                                    time_diff = abs((file_time - target_time).total_seconds())
                                    if time_diff < 300:  # 5 minutes
                                        match_found = True
                                        print(f"\n✅ Found matching recording (by timestamp)!")
                                        print(f"   Time difference: {time_diff:.0f} seconds")
                                        break
                                except Exception as e:
                                    if debug:
                                        print(f"\n   Debug: Error parsing timestamp: {e}")
                                    pass

                    # Strategy 3: Check if recording ID matches meeting UUID
                    if not match_found:
                        meeting_uuid = meeting.get("uuid", "")
                        if meeting_uuid and recording_id in meeting_uuid:
                            match_found = True
                            print(f"\n✅ Found matching recording (by UUID)!")

                    if match_found:
                        # Get the primary video file
                        for file in meeting.get("recording_files", []):
                            if file.get("file_type") in ["MP4", "M4A"]:
                                metadata = {
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

                                print(f"   Meeting: {metadata['topic']}")
                                print(f"   Date: {metadata['start_time']}")
                                print(f"   Type: {metadata['file_type']}")
                                print(f"   Size: {metadata['file_size'] / (1024*1024):.1f} MB")

                                return metadata

                # Check for next page
                next_page_token = data.get("next_page_token")
                if next_page_token:
                    params["next_page_token"] = next_page_token
                else:
                    break

            print(f"\n⚠️  Could not find recording with ID: {recording_id}")
            print(f"   Searched {page_count} pages, found {total_meetings} total recordings in date range")

            # Show debug info if enabled
            if debug and found_recordings:
                print(f"\n   📋 Recordings found in this date range:")
                for idx, rec in enumerate(found_recordings[:5], 1):  # Show first 5
                    print(f"      {idx}. {rec['topic']}")
                    print(f"         Time: {rec['start_time']}")
                    if rec['share_url']:
                        print(f"         Share URL: {rec['share_url'][:80]}...")
                    print(f"         UUID: {rec['uuid']}")
                if len(found_recordings) > 5:
                    print(f"      ... and {len(found_recordings) - 5} more")
                print(f"\n   💡 The recording you're looking for might:")
                print(f"      - Be from a different Zoom account")
                print(f"      - Have been deleted from cloud storage")
                print(f"      - Be in trash/archived")
                print(f"      - Require different access permissions")
            else:
                print(f"   ⚠️  No recordings found in the date range {from_date} to {to_date}")

            return None

        except Exception as e:
            print(f"\n❌ Error fetching recording metadata: {str(e)}")
            return None

    def download_file(self, download_url: str, output_path: Path,
                     show_progress: bool = True, use_auth: bool = True,
                     session: Optional[requests.Session] = None) -> bool:
        """
        Download a file from Zoom with optional authentication.

        Args:
            download_url: The download URL from Zoom API or share page
            output_path: Where to save the file
            show_progress: Whether to show download progress
            use_auth: Whether to add API access token (True for API downloads)
            session: Optional requests session to use (for share link downloads)

        Returns:
            True if download succeeded, False otherwise
        """
        # Build the URL
        if use_auth:
            # Ensure we have an access token
            if not self.access_token:
                self.get_access_token()

            # Add access token to URL
            if "?" in download_url:
                url = f"{download_url}&access_token={self.access_token}"
            else:
                url = f"{download_url}?access_token={self.access_token}"
        else:
            url = download_url

        # Use provided session or create new one
        requester = session if session else requests

        try:
            print(f"📥 Downloading to: {output_path.name}")
            response = requester.get(url, stream=True, allow_redirects=True)

            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if show_progress and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            downloaded_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            print(f"\r   Progress: {progress:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)", end='')

                if show_progress:
                    print()  # New line after progress
                print(f"✅ Successfully downloaded to: {output_path}")
                return True
            else:
                print(f"❌ Download failed: {response.status_code}")
                if response.status_code == 404:
                    print(f"   💡 The download URL might have expired or been moved")
                return False

        except Exception as e:
            print(f"❌ Download error: {str(e)}")
            return False

    def download_from_share_url_direct(self, share_url: str,
                                      custom_filename: Optional[str] = None) -> Optional[Path]:
        """
        Attempt to download directly from a share URL using web scraping.
        This is a fallback when API search doesn't find the recording.

        Args:
            share_url: The Zoom share URL
            custom_filename: Optional custom filename (without extension)

        Returns:
            Path to downloaded file, or None if download failed
        """
        print(f"\n🔄 Attempting direct download from share URL...")

        try:
            # Access the share page to get download URL
            session = requests.Session()
            response = session.get(share_url, allow_redirects=True)

            if response.status_code != 200:
                print(f"❌ Could not access share URL: {response.status_code}")
                return None

            # Try to find download link in the page
            from urllib.parse import unquote
            page_content = response.text

            # Look for download URL patterns in the HTML
            download_patterns = [
                r'https://[^"\']+\.zoom\.us/rec/download/[^"\']+',
                r'https://[^"\']+\.cloudfront\.net/[^"\']+\.mp4[^"\']*',
                r'"downloadUrl":"([^"]+)"',
                r'"playUrl":"([^"]+)"'
            ]

            import re
            download_url = None
            for pattern in download_patterns:
                match = re.search(pattern, page_content)
                if match:
                    download_url = match.group(1) if '(' in pattern else match.group(0)
                    download_url = unquote(download_url)
                    break

            if download_url:
                print(f"✅ Found download URL via share page")
                # Determine output filename
                if custom_filename:
                    filename = f"{custom_filename}.mp4"
                else:
                    recording_id = self.extract_recording_id_from_share_url(share_url)
                    filename = f"{recording_id}.mp4"

                output_path = self.output_dir / filename
                # Use session and don't add API auth token
                if self.download_file(download_url, output_path, use_auth=False, session=session):
                    return output_path
                else:
                    return None
            else:
                print(f"❌ Could not find download URL in share page")
                print(f"   💡 The recording might require password or be restricted")
                return None

        except Exception as e:
            print(f"❌ Error during direct download: {str(e)}")
            return None

    def download_from_share_url(self, share_url: str,
                               custom_filename: Optional[str] = None) -> Optional[Path]:
        """
        Download a recording from a Zoom share URL.

        This method tries two approaches:
        1. Search for the recording in the authenticated user's cloud recordings (API)
        2. If not found, attempt direct download from the share URL (web scraping)

        Args:
            share_url: The Zoom share URL
            custom_filename: Optional custom filename (without extension)

        Returns:
            Path to downloaded file, or None if download failed
        """
        print(f"\n{'='*70}")
        print(f"DOWNLOADING ZOOM RECORDING")
        print(f"{'='*70}")
        print(f"Share URL: {share_url}")
        print()

        # Step 1: Try to get recording metadata from API
        metadata = self.get_recording_metadata(share_url)

        if metadata:
            # Step 2: Determine output filename
            if custom_filename:
                filename = custom_filename
            else:
                # Use meeting ID and topic for filename
                safe_topic = "".join(c for c in metadata['topic'] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_topic = safe_topic.replace(' ', '_')
                filename = f"{metadata['meeting_id']}_{safe_topic}"

            # Add file extension
            file_extension = ".mp4" if metadata['file_type'] == "MP4" else ".m4a"
            output_path = self.output_dir / f"{filename}{file_extension}"

            # Step 3: Download the file
            print()
            if self.download_file(metadata['download_url'], output_path):
                return output_path

        # If API method failed, try direct download from share URL
        print(f"\n⚠️  API search failed. Trying direct download method...")
        print(f"   (The recording might be from a different Zoom account)")
        return self.download_from_share_url_direct(share_url, custom_filename)

    def download_multiple(self, share_urls: List[str]) -> List[Dict]:
        """
        Download multiple recordings from a list of share URLs.

        Args:
            share_urls: List of Zoom share URLs

        Returns:
            List of dictionaries with download results for each URL
        """
        results = []

        print(f"\n{'='*70}")
        print(f"BATCH DOWNLOAD: {len(share_urls)} recordings")
        print(f"{'='*70}\n")

        for idx, share_url in enumerate(share_urls, 1):
            print(f"\n[{idx}/{len(share_urls)}] Processing...")

            try:
                output_path = self.download_from_share_url(share_url)

                if output_path:
                    results.append({
                        "share_url": share_url,
                        "status": "success",
                        "output_path": str(output_path),
                        "error": None
                    })
                else:
                    results.append({
                        "share_url": share_url,
                        "status": "failed",
                        "output_path": None,
                        "error": "Download failed"
                    })

            except Exception as e:
                print(f"❌ Unexpected error: {str(e)}")
                results.append({
                    "share_url": share_url,
                    "status": "error",
                    "output_path": None,
                    "error": str(e)
                })

            # Brief pause between downloads to avoid rate limiting
            if idx < len(share_urls):
                time.sleep(1)

        # Print summary
        print(f"\n{'='*70}")
        print("DOWNLOAD SUMMARY")
        print(f"{'='*70}")
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"{'='*70}\n")

        return results


# Helper function to load from environment variables
def from_env(output_dir: str = "recordings") -> ZoomDownloader:
    """
    Create a ZoomDownloader instance from environment variables.

    Required environment variables:
        ZOOM_ACCOUNT_ID
        ZOOM_CLIENT_ID
        ZOOM_CLIENT_SECRET
        ZOOM_USER_ID

    Args:
        output_dir: Directory to save downloaded recordings

    Returns:
        Configured ZoomDownloader instance
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, rely on existing env vars

    required_vars = [
        "ZOOM_ACCOUNT_ID",
        "ZOOM_CLIENT_ID",
        "ZOOM_CLIENT_SECRET",
        "ZOOM_USER_ID"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return ZoomDownloader(
        account_id=os.getenv("ZOOM_ACCOUNT_ID"),
        client_id=os.getenv("ZOOM_CLIENT_ID"),
        client_secret=os.getenv("ZOOM_CLIENT_SECRET"),
        user_id=os.getenv("ZOOM_USER_ID"),
        output_dir=output_dir
    )
