# Structured Output Format

The pipeline exports video segmentations in two structured formats for easy querying and analysis.

## Output Files

### 1. Master CSV File
**`structured_output/all_videos_structured.csv`**

One row per video with columns:
- Video_Name
- Date
- Teacher
- Duration_Minutes
- Overall_Summary
- **Salam_Time_Ice_Breaker** (full text)
- **Discussion_Topic** (full text)
- **Quran_Recitation** (full text)
- **Arabic** (full text)
- **Worship** (full text)

**Use this for:**
- Excel/Google Sheets analysis
- Searching across all videos
- Creating reports
- Quick overview of all content

### 2. Individual JSON Files
**`structured_output/[VideoName]_structured.json`**

One file per video with detailed structure:

```json
{
  "video_name": "Ibn Batuta 1 and 2",
  "date": "Mar_22_2020",
  "teacher": "Marwa Elshamy",
  "duration_minutes": 45.2,
  "overall_summary": "Class about Ibn Battuta's travels...",
  "detected_order": ["Salam Time/Ice Breaker", "Discussion Topic", ...],
  "sections": {
    "Salam Time/Ice Breaker": {
      "text": "Full transcript text for this section...",
      "word_count": 234,
      "start_time": "00:00",
      "end_time": "02:30",
      "summary": "Brief summary..."
    },
    "Discussion Topic": {
      "text": "Full transcript text for discussion...",
      "word_count": 1523,
      "start_time": "02:30",
      "end_time": "25:45",
      "summary": "Main lesson content..."
    },
    ...
  }
}
```

**Use this for:**
- Programmatic access
- Building applications
- Detailed analysis per video
- Preserving all metadata

## Example Usage

### Excel/Google Sheets

1. Open `all_videos_structured.csv`
2. Each row = one video
3. Each column = one section's full text
4. Use filters/search to find specific content

Example queries:
- "Show me all videos mentioning 'Hijrah'"
- "Find all Arabic sections"
- "Which videos have Quran recitation?"

### Python Analysis

```python
import json
import pandas as pd
from pathlib import Path

# Load all videos from CSV
df = pd.read_csv("structured_output/all_videos_structured.csv")

# Search across all Discussion sections
quran_videos = df[df['Quran_Recitation'].str.contains('Surah', na=False)]

# Get all Discussion texts
discussion_texts = df['Discussion_Topic'].dropna().tolist()

# Load individual video JSON
with open("structured_output/Ibn_Batuta_1_and_2_structured.json") as f:
    video = json.load(f)
    print(video['sections']['Discussion Topic']['text'])
```

### Create Manual/Compilation

```python
from structured_export import load_all_videos_from_json_dir, create_manual_by_section

# Load all videos
videos = load_all_videos_from_json_dir(Path("structured_output"))

# Create a manual with all Quran Recitation sections
create_manual_by_section(
    videos,
    "Quran Recitation",
    Path("quran_recitation_manual.md")
)

# Create a manual with all Discussion sections
create_manual_by_section(
    videos,
    "Discussion Topic",
    Path("discussion_topics_manual.md")
)
```

### Query Specific Sections

```python
from structured_export import load_all_videos_from_json_dir, query_section_text

videos = load_all_videos_from_json_dir(Path("structured_output"))

# Get all Arabic lesson texts
arabic_texts = query_section_text(videos, "Arabic")

# Get all Worship texts
worship_texts = query_section_text(videos, "Worship")

# Analyze word counts
for video in videos:
    for section_type, section_data in video['sections'].items():
        print(f"{video['video_name']} - {section_type}: {section_data['word_count']} words")
```

## Data Format Details

### Section Types (Always These 5)

1. **Salam Time/Ice Breaker**
   - Greetings, introductions
   - Attendance, casual conversation

2. **Discussion Topic**
   - Main lesson content
   - Teaching, Q&A, core material

3. **Quran Recitation**
   - Reading/reciting Quranic verses
   - Studying Quran

4. **Arabic**
   - Arabic language learning
   - Vocabulary, grammar

5. **Worship**
   - Prayer, dua
   - Spiritual practices

### Missing Sections

If a section doesn't exist in a video:
- CSV: Empty cell
- JSON: Section not included in `sections` object

## Storage & Cost

### Storage Size Estimates

For a 1-hour video with transcript:
- JSON file: ~50-100 KB
- CSV row: ~20-50 KB (in master file)

For 100 videos:
- Total JSON: ~5-10 MB
- Master CSV: ~2-5 MB

**Very cheap to store!** Can easily store thousands of videos.

### Database Alternative

For very large collections (1000+ videos), consider using:
- SQLite database
- PostgreSQL with full-text search
- Elasticsearch for advanced search

I can help set this up if needed.

## Future Analysis

This format makes it easy to:

### 1. Create Manuals
Combine all sections of a type into teaching manuals:
```
Quran Recitation Manual = All Quran sections from all videos
Arabic Language Manual = All Arabic sections from all videos
```

### 2. Search & Discover
- "Find all videos about Hajj"
- "Which videos cover specific Surahs?"
- "Show me all Arabic vocabulary lessons"

### 3. Build Applications
- Web interface to browse videos by section
- Search across all transcripts
- Generate study guides automatically

### 4. Analytics
- Which topics are covered most?
- Average time spent on each section type
- Teacher comparison
- Content gaps analysis

## Next Steps

After processing all your videos, you'll have:
1. **One master CSV** with all videos and their segmented text
2. **Individual JSON files** for each video with detailed data
3. **Ready for manual creation** - just pick a section type and combine texts

Example:
```bash
# Process all videos (coming soon)
python batch_pipeline_from_csv.py your_recordings.csv

# Result: structured_output/all_videos_structured.csv
# Open in Excel, search/analyze, create manuals!
```

## Cost Estimate

For 100 videos (1 hour each):
- Transcription: ~$36 (Whisper API)
- Segmentation: ~$0.30 (Claude API)
- Storage: ~$0.01/month (S3/Google Drive)
- **Total: ~$37 one-time + pennies/month storage**

Very affordable for a comprehensive video library!
