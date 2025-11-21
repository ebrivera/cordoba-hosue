"""
Video Transcription Module

Supports multiple transcription services:
- OpenAI Whisper API (recommended, most accurate)
- Local Whisper (free but slower)
- Assembly AI (alternative)

Setup:
    pip install openai --break-system-packages

    Add to .env:
    OPENAI_API_KEY=your_key_here
"""

import os
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

    def transcribe_with_whisper_api(self, video_path: Path) -> Dict:
        """
        Transcribe video using OpenAI Whisper API.

        Args:
            video_path: Path to video file

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

        client = OpenAI(api_key=self.api_key)

        # Open the video file
        with open(video_path, "rb") as f:
            print(f"   Uploading file...")

            # Use timestamp granularities for detailed timing
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

        result = {
            "text": transcript.text,
            "segments": segments,
            "language": getattr(transcript, 'language', 'unknown'),
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
