"""
Export segmented videos to structured formats for analysis and manual creation.

Creates organized data structures where you can easily access the text
for each section of each video.

Formats:
- CSV: One row per video with columns for each section's text
- JSON: Structured data with full text for each section
"""

import json
import csv
from pathlib import Path
from typing import Dict, List


def export_to_structured_csv(segmentation: Dict, metadata: Dict, output_path: Path):
    """
    Export segmentation to CSV format with full text for each section.

    CSV Format:
    Video_Name | Date | Teacher | Duration | Salam_Text | Discussion_Text | Quran_Text | Arabic_Text | Worship_Text

    Args:
        segmentation: Segmentation dictionary with sections
        metadata: Video metadata (name, date, teacher, etc.)
        output_path: Path to output CSV file
    """

    # Define the 5 sections
    section_types = [
        "Salam Time/Ice Breaker",
        "Discussion Topic",
        "Quran Recitation",
        "Arabic",
        "Worship"
    ]

    # Extract text for each section (empty string if not present)
    section_texts = {}
    for section_type in section_types:
        matching_section = None
        for section in segmentation.get('sections', []):
            if section['type'] == section_type:
                matching_section = section
                break

        if matching_section:
            section_texts[section_type] = matching_section.get('text', '')
        else:
            section_texts[section_type] = ''

    # Check if file exists to determine if we need header
    file_exists = output_path.exists()

    # Write to CSV (append mode)
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header if new file
        if not file_exists:
            writer.writerow([
                'Video_Name',
                'Date',
                'Teacher',
                'Duration_Minutes',
                'Overall_Summary',
                'Salam_Time_Ice_Breaker',
                'Discussion_Topic',
                'Quran_Recitation',
                'Arabic',
                'Worship'
            ])

        # Write data row
        writer.writerow([
            metadata.get('name', ''),
            metadata.get('date', ''),
            metadata.get('teacher', ''),
            metadata.get('duration_minutes', ''),
            segmentation.get('overall_summary', ''),
            section_texts.get('Salam Time/Ice Breaker', ''),
            section_texts.get('Discussion Topic', ''),
            section_texts.get('Quran Recitation', ''),
            section_texts.get('Arabic', ''),
            section_texts.get('Worship', '')
        ])

    print(f"✅ Appended to CSV: {output_path}")


def export_to_structured_json(segmentation: Dict, metadata: Dict, output_path: Path):
    """
    Export segmentation to structured JSON format.

    JSON Format:
    {
      "video_name": "...",
      "date": "...",
      "sections": {
        "Salam Time/Ice Breaker": {
          "text": "full text...",
          "word_count": 123,
          "start_time": "00:00",
          "end_time": "02:30"
        },
        ...
      }
    }
    """

    # Build structured output
    structured = {
        "video_name": metadata.get('name', ''),
        "date": metadata.get('date', ''),
        "teacher": metadata.get('teacher', ''),
        "duration_minutes": metadata.get('duration_minutes', 0),
        "overall_summary": segmentation.get('overall_summary', ''),
        "detected_order": segmentation.get('detected_order', []),
        "sections": {}
    }

    # Add each section
    for section in segmentation.get('sections', []):
        section_type = section['type']
        structured['sections'][section_type] = {
            "text": section.get('text', ''),
            "word_count": section.get('word_count', 0),
            "start_time": section.get('start_time', ''),
            "end_time": section.get('end_time', ''),
            "summary": section.get('summary', '')
        }

    # Write to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)

    print(f"✅ Exported structured JSON: {output_path}")


def load_all_videos_from_json_dir(json_dir: Path) -> List[Dict]:
    """
    Load all structured JSON files from a directory.

    Returns:
        List of video dictionaries with full text for each section
    """
    videos = []
    for json_file in json_dir.glob("*_structured.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            videos.append(json.load(f))

    return videos


def query_section_text(videos: List[Dict], section_type: str) -> List[str]:
    """
    Extract all text for a specific section across all videos.

    Args:
        videos: List of video dictionaries
        section_type: One of the 5 section types

    Returns:
        List of texts for that section from all videos
    """
    texts = []
    for video in videos:
        if section_type in video.get('sections', {}):
            text = video['sections'][section_type].get('text', '')
            if text:
                texts.append(text)

    return texts


def create_manual_by_section(videos: List[Dict], section_type: str, output_path: Path):
    """
    Create a document with all text from one section type across all videos.

    Example: All "Quran Recitation" sections from all videos combined.
    """
    texts = query_section_text(videos, section_type)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {section_type} - Combined Content\n\n")
        f.write(f"Total videos: {len(texts)}\n")
        f.write(f"{'='*70}\n\n")

        for i, text in enumerate(texts, 1):
            f.write(f"## Video {i}\n\n")
            f.write(f"{text}\n\n")
            f.write(f"{'-'*70}\n\n")

    print(f"✅ Created manual: {output_path}")


# Example usage functions
def export_video_segmentation(
    segmentation: Dict,
    video_name: str,
    date: str,
    teacher: str = "",
    duration_minutes: float = 0,
    output_dir: Path = Path("structured_output")
):
    """
    Convenience function to export a video's segmentation to both formats.

    Args:
        segmentation: The segmentation result
        video_name: Name of the video
        date: Date string
        teacher: Teacher name
        duration_minutes: Video duration
        output_dir: Directory to save outputs
    """
    output_dir.mkdir(exist_ok=True)

    metadata = {
        "name": video_name,
        "date": date,
        "teacher": teacher,
        "duration_minutes": duration_minutes
    }

    # Create safe filename
    safe_name = "".join(c for c in video_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')

    # Export to JSON (one file per video)
    json_path = output_dir / f"{safe_name}_structured.json"
    export_to_structured_json(segmentation, metadata, json_path)

    # Append to master CSV (one row per video, all videos in one file)
    csv_path = output_dir / "all_videos_structured.csv"
    export_to_structured_csv(segmentation, metadata, csv_path)

    print(f"\n✅ Exported structured data:")
    print(f"   JSON: {json_path}")
    print(f"   CSV:  {csv_path}")


if __name__ == "__main__":
    print("""
Example usage:

# Export one video
from structured_export import export_video_segmentation
export_video_segmentation(
    segmentation=my_segmentation,
    video_name="Ibn Battuta Class",
    date="2020-03-22",
    teacher="Marwa Elshamy",
    duration_minutes=45
)

# Later, query all videos
from structured_export import load_all_videos_from_json_dir, query_section_text
videos = load_all_videos_from_json_dir(Path("structured_output"))
quran_texts = query_section_text(videos, "Quran Recitation")

# Create a manual from one section
from structured_export import create_manual_by_section
create_manual_by_section(videos, "Discussion Topic", Path("discussion_manual.md"))
""")
