# Video Processing Pipeline

Complete pipeline to download, transcribe, and segment Islamic educational videos.

## Pipeline Steps

1. **Download** - Download Zoom recordings using share URLs or UUIDs
2. **Transcribe** - Convert video to text with timestamps using Whisper API
3. **Segment** - Use Claude AI to identify 5 class sections

## The 5 Sections

The AI will identify and segment videos into these sections (in any order):

1. **Salam Time/Ice Breaker** - Greetings, introductions, casual conversation
2. **Discussion Topic** - Main lesson content, teaching, Q&A
3. **Quran Recitation** - Reading or studying Quranic verses
4. **Arabic** - Arabic language learning, vocabulary, grammar
5. **Worship** - Prayer time, dua, spiritual practices

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys:
- **Zoom API** (for downloading):
  - Get from: https://marketplace.zoom.us/develop/create
  - Create a "Server-to-Server OAuth" app
  - Grant scope: `cloud_recording:read:list_user_recordings:master`

- **OpenAI API** (for transcription):
  - Get from: https://platform.openai.com/api-keys
  - Used for Whisper API transcription
  - Cost: ~$0.006 per minute of audio

- **Anthropic API** (for segmentation):
  - Get from: https://console.anthropic.com/
  - Used for Claude AI segmentation
  - Cost: ~$0.003 per video (for Claude Sonnet)

### 3. Test with One Video

```bash
python pipeline_one_video.py
```

This will:
1. Download the test video from your CSV
2. Transcribe it with Whisper
3. Segment it with Claude AI
4. Create output files in `recordings/`, `transcripts/`, and `segments/`

## Output Files

For each video, you'll get:

```
recordings/
  Mar_22_2020_Ibn_Batuta_1_and_2.mp4

transcripts/
  Mar_22_2020_Ibn_Batuta_1_and_2_transcript.json  # Full transcript with timestamps
  Mar_22_2020_Ibn_Batuta_1_and_2_transcript.txt   # Readable format

segments/
  Mar_22_2020_Ibn_Batuta_1_and_2_segments.json    # Segmentation data
  Mar_22_2020_Ibn_Batuta_1_and_2_segments.txt     # Readable format
```

## Segmentation Output Example

```json
{
  "sections": [
    {
      "type": "Salam Time/Ice Breaker",
      "start_time": "00:00",
      "end_time": "02:30",
      "summary": "Teacher greets students and takes attendance..."
    },
    {
      "type": "Discussion Topic",
      "start_time": "02:30",
      "end_time": "25:45",
      "summary": "Main lesson about Ibn Battuta's travels..."
    },
    {
      "type": "Quran Recitation",
      "start_time": "25:45",
      "end_time": "32:10",
      "summary": "Students recite Surah Al-Kahf verses..."
    }
  ],
  "overall_summary": "Class covering Ibn Battuta's travels with Quran recitation",
  "detected_order": ["Salam Time/Ice Breaker", "Discussion Topic", "Quran Recitation"]
}
```

## Costs

Approximate costs per 1-hour video:

- **Download**: Free (uses your Zoom account)
- **Transcription**: ~$0.36 (Whisper API at $0.006/min)
- **Segmentation**: ~$0.003 (Claude Sonnet)
- **Total**: ~$0.36 per hour of video

For 100 hours of video: ~$36

## Batch Processing

Once you've tested with one video, you can process your entire CSV:

```bash
# Coming soon: batch_pipeline_from_csv.py
# This will process all videos in your CSV file
```

## Troubleshooting

### "OPENAI_API_KEY not found"
- Make sure you've added it to your `.env` file
- Get a key from https://platform.openai.com/api-keys

### "ANTHROPIC_API_KEY not found"
- Make sure you've added it to your `.env` file
- Get a key from https://console.anthropic.com/

### Transcription fails
- Check that the video file is valid (can play it)
- Whisper API supports: mp4, mp3, m4a, wav, webm
- Max file size: 25 MB (API will handle longer videos in chunks)

### Segmentation looks wrong
- The AI might misidentify sections if:
  - Video has unusual structure
  - Audio quality is poor
  - Content doesn't match the 5 categories
- You can manually review and edit the segments JSON file

## Advanced Usage

### Use Individual Components

```python
# Just download
from zoom_downloader import from_env
downloader = from_env(output_dir="recordings")
video_path = downloader.download_by_uuid("YOUR_UUID")

# Just transcribe
from transcriber import transcribe_video
transcript = transcribe_video("path/to/video.mp4")

# Just segment
from segmenter import segment_video
segmentation = segment_video("path/to/transcript.json")
```

### Custom Segmentation Categories

To use different categories, edit `segmenter.py` and modify the prompt in `_create_segmentation_prompt()`.

## Support

For issues or questions, see the main README or create an issue on GitHub.
