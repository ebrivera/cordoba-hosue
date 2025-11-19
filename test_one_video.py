#!/usr/bin/env python3
"""
Test downloading ONE video from your CSV to make sure it works.

This is a quick test before running the full batch download.
"""

from zoom_downloader import from_env

# Test with the first video from your CSV
TEST_SHARE_URL = "https://us02web.zoom.us/rec/share/AtdgqzZZVDaxgQrZ9zi8LxDBmkmR9zAywXyDr-BmAusL5MqYgycZw2A3gBwhFVwl.IMF_KocBJaohnImb?startTime=1584887394000"
TEST_NAME = "Ibn Batuta 1 and 2"
TEST_DATE = "Mar_22_2020"

def test_single_download():
    """Test downloading one video from the CSV"""

    print("="*70)
    print("TEST: Download One Video from CSV")
    print("="*70)
    print(f"Video: {TEST_NAME}")
    print(f"Date: {TEST_DATE}")
    print(f"Share URL: {TEST_SHARE_URL[:60]}...")
    print("="*70)
    print()

    # Create downloader
    downloader = from_env(output_dir="recordings")

    # Try to download with a nice filename
    custom_filename = f"{TEST_DATE}_{TEST_NAME.replace(' ', '_')}"

    output_path = downloader.download_from_share_url(
        TEST_SHARE_URL,
        custom_filename=custom_filename
    )

    if output_path:
        print(f"\n{'='*70}")
        print("✅ SUCCESS! Video downloaded successfully!")
        print(f"{'='*70}")
        print(f"File: {output_path}")
        print(f"\n💡 This proves the download system works!")
        print(f"   You can now use batch_download_from_csv.py for all videos")
        return True
    else:
        print(f"\n{'='*70}")
        print("❌ FAILED to download")
        print(f"{'='*70}")
        print("\nPossible issues:")
        print("1. Recording might be from a different Zoom account")
        print("2. Recording might have been deleted")
        print("3. ZOOM_USER_ID in .env might not match the recording owner")
        print("\nLet's check your account's recordings...")

        # Try listing recordings from that time period to see what's available
        print(f"\n{'='*70}")
        print("Checking recordings from March 2020...")
        print(f"{'='*70}")

        recordings = downloader.list_recordings(
            from_date="2020-03-01",
            to_date="2020-03-31",
            max_results=50
        )

        if recordings:
            print(f"\n📋 Found {len(recordings)} recordings in March 2020:")
            for i, rec in enumerate(recordings[:5], 1):
                print(f"\n{i}. {rec['topic']}")
                print(f"   Date: {rec['start_time']}")
                print(f"   UUID: {rec['meeting_uuid']}")
        else:
            print("\n⚠️  No recordings found in March 2020")
            print("   This might mean:")
            print("   - Recordings are from a different account")
            print("   - ZOOM_USER_ID in .env is incorrect")
            print("   - Recordings have been deleted")

        return False


if __name__ == "__main__":
    test_single_download()
