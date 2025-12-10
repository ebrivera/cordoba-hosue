"""
LLM-based Video Segmentation

Uses Claude API to analyze transcripts and segment them into
predefined sections (Salam/Ice breaker, Discussion, Quran, Arabic, Worship).

Setup:
    pip install anthropic --break-system-packages

    Add to .env:
    ANTHROPIC_API_KEY=your_key_here
"""

import os
import json
from pathlib import Path
from typing import Dict, List


class VideoSegmenter:
    """Segment video transcripts into sections using LLM"""

    def __init__(self, api_key: str = None):
        """
        Initialize segmenter.

        Args:
            api_key: Anthropic API key (or reads from ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or provided")

    def segment_transcript(self, transcript: Dict) -> Dict:
        """
        Segment transcript into 5 predefined sections.

        Args:
            transcript: Transcript dictionary with 'segments' and 'text'

        Returns:
            Dictionary with:
            - sections: List of identified sections with timestamps and FULL TEXT
            - summary: Overall summary
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Anthropic library not installed. Run: pip install anthropic")

        print(f"\n🤖 Analyzing transcript with Claude...")

        # Prepare the transcript text with timestamps
        transcript_text = self._format_for_analysis(transcript)

        # Create the prompt
        prompt = self._create_segmentation_prompt(transcript_text)

        # Call Claude API
        client = Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse the response
        result_text = response.content[0].text
        print(f"✅ Segmentation complete!")

        # Parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()

            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Could not parse JSON response. Using raw text.")
            result = {"raw_response": result_text, "sections": []}

        # Extract the actual text for each section
        print(f"📝 Extracting text for each section...")
        result = self._extract_section_texts(result, transcript)

        return result

    def _format_for_analysis(self, transcript: Dict) -> str:
        """Format transcript with timestamps for LLM analysis"""
        lines = []
        for seg in transcript['segments']:
            timestamp = self._format_timestamp(seg['start'])
            lines.append(f"[{timestamp}] {seg['text']}")
        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Parse MM:SS timestamp to seconds"""
        try:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + int(seconds)
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        except:
            return 0.0
        return 0.0

    def _extract_section_texts(self, segmentation: Dict, transcript: Dict) -> Dict:
        """
        Extract the actual transcript text for each identified section.

        Args:
            segmentation: The segmentation result from Claude
            transcript: The original transcript with timestamped segments

        Returns:
            Updated segmentation with 'text' field added to each section
        """
        if 'sections' not in segmentation or not segmentation['sections']:
            return segmentation

        # For each section, extract the text from transcript segments
        for section in segmentation['sections']:
            start_time = self._parse_timestamp(section.get('start_time', '00:00'))
            end_time = self._parse_timestamp(section.get('end_time', '00:00'))

            # Extract all transcript segments within this time range
            section_texts = []
            for seg in transcript.get('segments', []):
                seg_start = seg.get('start', 0)
                seg_end = seg.get('end', 0)

                # Check if this segment overlaps with the section
                if seg_start >= start_time and seg_end <= end_time:
                    section_texts.append(seg.get('text', '').strip())
                elif seg_start < end_time and seg_end > start_time:
                    # Partial overlap - include it
                    section_texts.append(seg.get('text', '').strip())

            # Join all texts for this section
            section['text'] = ' '.join(section_texts)
            section['word_count'] = len(section['text'].split())

            print(f"   {section['type']}: {section['word_count']} words")

        return segmentation

    def _create_segmentation_prompt(self, transcript_text: str) -> str:
        """Create the prompt for Claude to segment the video"""
        return f"""You are analyzing a transcript from an Islamic educational class video. Your task is to identify and segment the video into 5 distinct sections. These sections may appear in ANY order.

The 5 sections are:
1. **Salam Time/Ice Breaker** - Greetings, introductions, casual conversation, attendance, how are you doing
2. **Discussion Topic** - Main lesson content, teaching, Q&A about the topic
3. **Quran Recitation** - Reading, reciting, or studying Quranic verses
4. **Arabic** - Arabic language learning, vocabulary, grammar lessons
5. **Worship** - Prayer time, dua, spiritual practices

**Important Notes:**
- Sections can appear in ANY order (not necessarily 1-5)
- Some sections might be brief or missing entirely
- Look for natural transitions and topic changes
- Use the timestamps to identify section boundaries

Here is the transcript with timestamps:

{transcript_text}

**Your task:**
Analyze this transcript and identify which parts belong to which sections. For each section you identify:
1. Determine the start and end timestamps
2. Provide a brief summary of what happens in that section
3. Assign it to one of the 5 categories

Return your analysis as a JSON object with this structure:

```json
{{
  "sections": [
    {{
      "type": "Salam Time/Ice Breaker",
      "start_time": "00:00",
      "end_time": "02:30",
      "summary": "Brief description of this section"
    }},
    {{
      "type": "Discussion Topic",
      "start_time": "02:30",
      "end_time": "15:45",
      "summary": "Brief description of this section"
    }}
  ],
  "overall_summary": "1-2 sentence summary of the entire class",
  "detected_order": ["Salam Time/Ice Breaker", "Discussion Topic", ...]
}}
```

Only include sections that are actually present in the video. If a section is missing, don't include it.

Provide your analysis as valid JSON only."""

    def save_segmentation(self, segmentation: Dict, output_path: Path):
        """Save segmentation to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(segmentation, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved segmentation to: {output_path}")

    def format_segmentation_readable(self, segmentation: Dict) -> str:
        """Format segmentation as readable text"""
        lines = []
        lines.append("Video Segmentation")
        lines.append("=" * 70)
        lines.append("")

        if "overall_summary" in segmentation:
            lines.append(f"Summary: {segmentation['overall_summary']}")
            lines.append("")

        if "detected_order" in segmentation:
            lines.append(f"Section Order: {' → '.join(segmentation['detected_order'])}")
            lines.append("")

        lines.append("Sections:")
        lines.append("-" * 70)

        for i, section in enumerate(segmentation.get('sections', []), 1):
            lines.append(f"\n{i}. {section['type']}")
            lines.append(f"   Time: {section['start_time']} - {section['end_time']}")
            lines.append(f"   Summary: {section['summary']}")

        return "\n".join(lines)


def segment_video(transcript_path: Path, output_dir: Path = None) -> Dict:
    """
    Convenience function to segment a video transcript.

    Args:
        transcript_path: Path to transcript JSON file
        output_dir: Directory to save segmentation (default: same as transcript)

    Returns:
        Segmentation dictionary
    """
    # Load transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)

    # Segment
    segmenter = VideoSegmenter()
    segmentation = segmenter.segment_transcript(transcript)

    # Save segmentation
    if output_dir is None:
        output_dir = transcript_path.parent

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Save JSON
    json_path = output_dir / f"{transcript_path.stem.replace('_transcript', '')}_segments.json"
    segmenter.save_segmentation(segmentation, json_path)

    # Save readable text
    txt_path = output_dir / f"{transcript_path.stem.replace('_transcript', '')}_segments.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(segmenter.format_segmentation_readable(segmentation))
    print(f"💾 Saved readable segmentation to: {txt_path}")

    return segmentation


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python segmenter.py <transcript.json>")
        sys.exit(1)

    transcript_file = Path(sys.argv[1])
    if not transcript_file.exists():
        print(f"Error: File not found: {transcript_file}")
        sys.exit(1)

    segment_video(transcript_file)
