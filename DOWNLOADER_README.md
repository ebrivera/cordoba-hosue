# Zoom Video Downloader

A simple, focused tool for downloading Zoom cloud recordings.

## Quick Start

### 1. Install Dependencies

```bash
pip install requests python-dotenv --break-system-packages
```

### 2. Get Zoom API Credentials

1. Go to https://marketplace.zoom.us/develop/create
2. Create a **Server-to-Server OAuth** app
3. You'll need:
   - Account ID
   - Client ID
   - Client Secret
   - Your Zoom email address

### 3. Configure Credentials

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
ZOOM_ACCOUNT_ID=your_account_id_here
ZOOM_CLIENT_ID=your_client_id_here
ZOOM_CLIENT_SECRET=your_client_secret_here
ZOOM_USER_ID=your_email@example.com
```

### 4. Test Download

```bash
python test_download.py
```

This will download the test video to the `recordings/` folder.

## Usage

### Single Video Download

```python
from zoom_downloader import from_env

# Create downloader from .env file
downloader = from_env()

# Download a video
share_url = "https://us02web.zoom.us/rec/share/..."
output_path = downloader.download_from_share_url(share_url)

if output_path:
    print(f"Downloaded to: {output_path}")
```

### Multiple Videos (Batch Download)

```python
from zoom_downloader import from_env

# Create downloader
downloader = from_env()

# List of share URLs
urls = [
    "https://us02web.zoom.us/rec/share/...",
    "https://us02web.zoom.us/rec/share/...",
    # ... more URLs
]

# Download all
results = downloader.download_multiple(urls)

# Check results
for result in results:
    if result['status'] == 'success':
        print(f"✅ {result['output_path']}")
    else:
        print(f"❌ {result['error']}")
```

### Working with CSV Data

If you have a CSV with columns like in your example:
- Name of the Meeting
- Email
- Meeting ID
- Date
- Time
- Meeting Type
- Teacher
- **Share Link** ← This is what we need!

```python
import csv
from zoom_downloader import from_env

# Read CSV
with open('zoom_videos.csv', 'r') as f:
    reader = csv.DictReader(f)
    share_urls = [row['Share Link'] for row in reader]

# Download all
downloader = from_env()
results = downloader.download_multiple(share_urls)
```

## What Gets Downloaded

- Videos are saved to `recordings/` folder
- Filename format: `{meeting_id}_{topic}.mp4`
- Both MP4 (video) and M4A (audio-only) formats are supported

## Troubleshooting

### "Missing required environment variables"
Make sure you created a `.env` file with all required credentials.

### "Could not find recording"
- Make sure the share URL is from YOUR Zoom account (the one in ZOOM_USER_ID)
- Make sure the recording still exists in your cloud storage
- Check that your OAuth app has the correct scopes enabled

### "Failed to get access token"
- Double-check your Account ID, Client ID, and Client Secret
- Make sure your Server-to-Server OAuth app is activated
- Check that the app has the required scopes: `recording:read`

## Next Steps

After you can successfully download videos, you can:
1. Integrate with the transcription pipeline
2. Process batches from CSV files
3. Add automatic organization by date/topic
