#!/usr/bin/env python3
"""
Test downloading by UUID (the recommended method)

This demonstrates the better way to download recordings:
1. List all recordings to get their UUIDs
2. Download by UUID (much more reliable than share URLs)

Usage:
    1. Run this to see your recent recordings
    2. Copy a UUID and use it to download
"""

from zoom_downloader import from_env


def test_list_and_download():
    """List recordings and download one by UUID"""

    print("="*70)
    print("TEST: Download by UUID (RECOMMENDED METHOD)")
    print("="*70)
    print()

    # Create downloader
    downloader = from_env(output_dir="recordings")

    # Step 1: List recent recordings (last 30 days)
    print("STEP 1: Listing your recordings...\n")
    recordings = downloader.list_recordings(max_results=10)

    if not recordings:
        print("⚠️  No recordings found. Try expanding the date range.")
        return

    # Show the recordings
    print(f"\n{'='*70}")
    print("YOUR RECORDINGS")
    print(f"{'='*70}\n")

    for i, rec in enumerate(recordings, 1):
        print(f"{i}. {rec['topic']}")
        print(f"   UUID: {rec['meeting_uuid']}")
        print(f"   Date: {rec['start_time']}")
        print(f"   Duration: {rec['duration']} min")

        # Show file types
        file_types = set(f['file_type'] for f in rec['recording_files'])
        print(f"   Files: {', '.join(file_types)}")
        print()

    # Step 2: Download the first recording as a demo
    if recordings:
        print(f"\n{'='*70}")
        print("STEP 2: Downloading first recording by UUID...")
        print(f"{'='*70}\n")

        first_recording = recordings[0]
        uuid = first_recording['meeting_uuid']

        output_path = downloader.download_by_uuid(uuid)

        if output_path:
            print(f"\n🎉 SUCCESS! Downloaded to: {output_path}")
            print(f"\n💡 To download any recording, use:")
            print(f"   downloader.download_by_uuid('{uuid}')")
        else:
            print(f"\n❌ Download failed")


def test_specific_uuid():
    """
    Test downloading a specific UUID.
    Replace the UUID below with one from your account.
    """

    # EXAMPLE: Replace with actual UUID from list_recordings()
    TEST_UUID = "YOUR_UUID_HERE"

    if TEST_UUID == "YOUR_UUID_HERE":
        print("⚠️  Please run test_list_and_download() first to get a UUID")
        return

    downloader = from_env(output_dir="recordings")
    output_path = downloader.download_by_uuid(TEST_UUID)

    if output_path:
        print(f"✅ Downloaded to: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Download specific UUID from command line
        uuid = sys.argv[1]
        downloader = from_env(output_dir="recordings")
        downloader.download_by_uuid(uuid)
    else:
        # List and download demo
        test_list_and_download()
