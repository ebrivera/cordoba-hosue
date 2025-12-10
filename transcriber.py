"""
Video Transcription Module

Supports multiple transcription services:
- OpenAI Whisper API (recommended, most accurate)
- Handles large files by extracting audio first

Setup:
    pip install openai ffmpeg-python --break-system-packages

    Also install ffmpeg:
    - Mac: brew install ffmpeg
    - Ubuntu: apt-get install ffmpeg
    - Windows: Download from ffmpeg.org

    Add to .env:
    OPENAI_API_KEY=your_key_here
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import json


class VideoTranscriber:
    """Transcribe video files to text with timestamps"""

    def __init__(self, api_key: str = None):
        """
        Initialize transcriber.

        Args:
            api_key: OpenAI API key (or reads from OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or provided")

    def extract_audio(self, video_path: Path, output_path: Path = None) -> Path:
        """
        Extract audio from video as MP3 for Whisper API.

        Args:
            video_path: Path to video file
            output_path: Path to save audio (default: same name with .mp3)

        Returns:
            Path to extracted audio file
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_audio.mp3"

        print(f"🎵 Extracting audio from video...")
        print(f"   Input:  {video_path.name}")
        print(f"   Output: {output_path.name}")

        # Use ffmpeg to extract audio and compress
        # -vn: no video
        # -acodec libmp3lame: encode to MP3
        # -b:a 64k: 64 kbps (good quality, small size)
        # -ar 16000: 16kHz sample rate (Whisper works well with this)
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-b:a', '64k',  # 64 kbps
            '-ar', '16000',  # 16 kHz
            '-y',  # Overwrite output file
            str(output_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            # Get file size
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ Audio extracted: {size_mb:.1f} MB")

            # Check if still too large for Whisper API (25 MB limit)
            if size_mb > 24:
                print(f"⚠️  Audio is still large ({size_mb:.1f} MB)")
                print(f"   Whisper API limit is 25 MB")
                print(f"   This might fail - consider splitting the file")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise Exception(f"Failed to extract audio: {error_msg}")
        except FileNotFoundError:
            raise Exception(
                "ffmpeg not found. Install it:\n"
                "  Mac: brew install ffmpeg\n"
                "  Ubuntu: apt-get install ffmpeg\n"
                "  Windows: Download from ffmpeg.org"
            )

    def split_audio(self, audio_path: Path, max_size_mb: float = 24.0) -> List[Path]:
        """
        Split audio file into chunks under the size limit.

        Args:
            audio_path: Path to audio file
            max_size_mb: Maximum size per chunk in MB

        Returns:
            List of paths to audio chunks
        """
        # Get duration of the audio file
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        total_duration = float(result.stdout.decode('utf-8').strip())

        # Calculate file size and number of chunks needed
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        num_chunks = int(file_size_mb / max_size_mb) + 1

        print(f"📂 Splitting audio into {num_chunks} chunks...")
        print(f"   Total duration: {total_duration:.1f} seconds")

        chunk_duration = total_duration / num_chunks
        chunks = []

        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = audio_path.parent / f"{audio_path.stem}_chunk_{i+1}.mp3"

            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-acodec', 'copy',
                '-y',
                str(chunk_path)
            ]

            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            chunk_size = chunk_path.stat().st_size / (1024 * 1024)
            print(f"   Chunk {i+1}/{num_chunks}: {chunk_size:.1f} MB")
            chunks.append(chunk_path)

        return chunks

    def transcribe_with_whisper_api(self, video_path: Path, use_audio_extraction: bool = True) -> Dict:
        """
        Transcribe video using OpenAI Whisper API.

        Args:
            video_path: Path to video file
            use_audio_extraction: Extract audio first if file is large (default: True)

        Returns:
            Dictionary with:
            - text: Full transcript
            - segments: List of timed segments with text
            - language: Detected language
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")

        print(f"\n🎙️  Transcribing: {video_path.name}")
        print(f"   Using: OpenAI Whisper API")

        # Check file size
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        print(f"   File size: {file_size_mb:.1f} MB")

        # Extract audio if file is too large or if explicitly requested
        audio_file = video_path
        cleanup_audio = False

        if use_audio_extraction and file_size_mb > 24:
            print(f"   File exceeds 25 MB limit, extracting audio...")
            audio_file = self.extract_audio(video_path)
            cleanup_audio = True
        elif use_audio_extraction:
            print(f"   Extracting audio for better compression...")
            audio_file = self.extract_audio(video_path)
            cleanup_audio = True

        # Check if we need to split the audio
        audio_size_mb = audio_file.stat().st_size / (1024 * 1024)
        need_split = audio_size_mb > 24.0

        chunks_to_cleanup = []

        client = OpenAI(api_key=self.api_key)

        try:
            if need_split:
                print(f"   Audio still too large ({audio_size_mb:.1f} MB), splitting...")

                # Split into chunks
                chunks = self.split_audio(audio_file, max_size_mb=24.0)
                chunks_to_cleanup = chunks

                # Transcribe each chunk
                all_segments = []
                full_text = []
                time_offset = 0.0

                for i, chunk in enumerate(chunks, 1):
                    print(f"   Transcribing chunk {i}/{len(chunks)}...")

                    with open(chunk, "rb") as f:
                        chunk_transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=f,
                            response_format="verbose_json",
                            timestamp_granularities=["segment"]
                        )

                    # Add segments with time offset
                    if hasattr(chunk_transcript, 'segments'):
                        for seg in chunk_transcript.segments:
                            all_segments.append({
                                "start": seg.get("start", 0) + time_offset,
                                "end": seg.get("end", 0) + time_offset,
                                "text": seg.get("text", "").strip()
                            })

                        # Update time offset for next chunk
                        if chunk_transcript.segments:
                            last_seg = chunk_transcript.segments[-1]
                            time_offset += last_seg.get("end", 0)

                    full_text.append(chunk_transcript.text)

                # Combine results
                segments = all_segments
                combined_text = " ".join(full_text)
                language = getattr(chunk_transcript, 'language', 'unknown')

            else:
                # Single file transcription
                with open(audio_file, "rb") as f:
                    print(f"   Uploading file...")

                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"]
                    )

                # Extract segments with timestamps
                segments = []
                if hasattr(transcript, 'segments'):
                    for seg in transcript.segments:
                        segments.append({
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                            "text": seg.get("text", "").strip()
                        })

                combined_text = transcript.text
                language = getattr(transcript, 'language', 'unknown')

        finally:
            # Clean up chunks
            for chunk in chunks_to_cleanup:
                if chunk.exists():
                    chunk.unlink()

            # Clean up extracted audio file
            if cleanup_audio and audio_file.exists():
                print(f"   Cleaning up audio file...")
                audio_file.unlink()

        result = {
            "text": combined_text,
            "segments": segments,
            "language": language,
            "duration": segments[-1]["end"] if segments else 0
        }

        print(f"✅ Transcription complete!")
        print(f"   Language: {result['language']}")
        print(f"   Duration: {result['duration']:.1f} seconds")
        print(f"   Segments: {len(segments)}")

        return result

    def save_transcript(self, transcript: Dict, output_path: Path):
        """Save transcript to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved transcript to: {output_path}")

    def format_transcript_readable(self, transcript: Dict) -> str:
        """Format transcript as readable text with timestamps"""
        lines = []
        lines.append(f"Transcript - Duration: {transcript['duration']:.1f}s")
        lines.append("=" * 70)
        lines.append("")

        for seg in transcript['segments']:
            timestamp = self._format_timestamp(seg['start'])
            lines.append(f"[{timestamp}] {seg['text']}")

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


def transcribe_video(video_path: Path, output_dir: Path = None) -> Dict:
    """
    Convenience function to transcribe a video.

    Args:
        video_path: Path to video file
        output_dir: Directory to save transcript (default: same as video)

    Returns:
        Transcript dictionary
    """
    transcriber = VideoTranscriber()

    # Transcribe
    transcript = transcriber.transcribe_with_whisper_api(video_path)

    # Save transcript
    if output_dir is None:
        output_dir = video_path.parent

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Save JSON
    json_path = output_dir / f"{video_path.stem}_transcript.json"
    transcriber.save_transcript(transcript, json_path)

    # Save readable text
    txt_path = output_dir / f"{video_path.stem}_transcript.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(transcriber.format_transcript_readable(transcript))
    print(f"💾 Saved readable transcript to: {txt_path}")

    return transcript


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <video_file>")
        sys.exit(1)

    video_file = Path(sys.argv[1])
    if not video_file.exists():
        print(f"Error: File not found: {video_file}")
        sys.exit(1)

    transcribe_video(video_file)
