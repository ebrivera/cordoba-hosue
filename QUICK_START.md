# Zoom Downloader - Quick Start Guide

## Why Use UUIDs Instead of Share Links?

**Share Links are unreliable** because:
- ❌ They can be from different Zoom accounts
- ❌ Share tokens don't map cleanly to API identifiers
- ❌ They may expire or change over time

**Meeting UUIDs are better** because:
- ✅ They're the actual unique identifiers in Zoom's system
- ✅ They work reliably with the API
- ✅ They never change for a recording
- ✅ You can only access recordings from YOUR account (secure)

## Quick Start

### 1. Export All Your Recordings to CSV

```bash
# List last 30 days (default)
python list_recordings.py

# List specific date range (e.g., all of 2020)
python list_recordings.py --from 2020-01-01 --to 2020-12-31

# Custom output file
python list_recordings.py --from 2024-01-01 --output 2024_recordings.csv
```

This creates a CSV file with:
- **Meeting UUID** ← Use this for downloads!
- Meeting ID
- Topic/Title
- Start Time
- Duration
- File Types
- Size

### 2. Download by UUID (Recommended)

```python
from zoom_downloader import from_env

# Create downloader
downloader = from_env(output_dir="recordings")

# Download using UUID from the CSV
downloader.download_by_uuid("YOUR_UUID_HERE")
```

Or from command line:

```bash
python test_download_by_uuid.py YOUR_UUID_HERE
```

### 3. Download by Share URL (Fallback)

If you only have a share URL, the downloader will try:
1. Search your account by timestamp/UUID
2. If not found, attempt direct download (web scraping)

```python
from zoom_downloader import from_env

downloader = from_env(output_dir="recordings")
downloader.download_from_share_url("https://zoom.us/rec/share/...")
```

## Example Workflow

```bash
# Step 1: Export all recordings to CSV
python list_recordings.py --from 2020-01-01 --to 2024-12-31

# Step 2: Open zoom_recordings.csv in Excel/Numbers
# Step 3: Find the recording you want
# Step 4: Copy the UUID

# Step 5: Download it
python test_download_by_uuid.py "UUID_FROM_CSV"
```

## Python API Examples

### List and Download

```python
from zoom_downloader import from_env

# Create downloader
downloader = from_env(output_dir="recordings")

# Get all recordings from 2024
recordings = downloader.list_recordings(
    from_date="2024-01-01",
    to_date="2024-12-31",
    max_results=500
)

# Print them
for rec in recordings:
    print(f"{rec['topic']} - {rec['meeting_uuid']}")

# Download specific ones
for rec in recordings:
    if "important" in rec['topic'].lower():
        print(f"Downloading: {rec['topic']}")
        downloader.download_by_uuid(rec['meeting_uuid'])
```

### Batch Download All Recordings

```python
from zoom_downloader import from_env

downloader = from_env(output_dir="recordings")

# Get all recordings
recordings = downloader.list_recordings(
    from_date="2020-01-01",
    max_results=1000
)

# Download them all
for i, rec in enumerate(recordings, 1):
    print(f"\n[{i}/{len(recordings)}] Downloading: {rec['topic']}")
    downloader.download_by_uuid(rec['meeting_uuid'])
```

## Troubleshooting

### "No recordings found"
- Check your date range - recordings might be older/newer
- Verify ZOOM_USER_ID in .env is correct (must be the account that owns recordings)
- Check that recordings haven't been deleted from cloud storage

### "Could not find recording"
- The UUID might be from a different account
- Recording might have been deleted
- Check the recording still exists in Zoom web portal

### Share URL doesn't work
- Share URL might be from a different Zoom account than ZOOM_USER_ID
- Use `list_recordings()` to get UUIDs from your actual account instead

## Environment Setup

Required `.env` file:

```bash
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_USER_ID=your_email@example.com  # Must own the recordings!
```

Get these from: https://marketplace.zoom.us/develop/create
- Create a Server-to-Server OAuth app
- Grant scope: `recording:read:admin` or `recording:read`
