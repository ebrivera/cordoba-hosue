#!/usr/bin/env python3
"""
Test script for downloading a single Zoom recording

Usage:
    1. Copy .env.example to .env and fill in your credentials
    2. Run: python test_download.py
"""

from zoom_downloader import from_env

# Test video from user
TEST_VIDEO_URL = "https://us02web.zoom.us/rec/share/K87Fx1wSLflLf6-jeKItz-0Tct2myO4zW560TEepLTNqQwMxTs7humUhKoBpVKvJ.hm3Dbn-mRz3TpThK?startTime=1604240384000"

def test_single_download():
    """Test downloading a single video"""
    print("🚀 Testing Zoom Video Download\n")

    # Create downloader from environment variables
    downloader = from_env(output_dir="recordings")

    # Download the test video
    output_path = downloader.download_from_share_url(TEST_VIDEO_URL)

    if output_path:
        print(f"\n🎉 SUCCESS! Video downloaded to: {output_path}")
        return True
    else:
        print(f"\n❌ FAILED to download video")
        return False


def test_multiple_downloads():
    """Test downloading multiple videos"""
    print("🚀 Testing Batch Download\n")

    # Example URLs from the user's CSV data
    test_urls = [
        "https://us02web.zoom.us/rec/share/K87Fx1wSLflLf6-jeKItz-0Tct2myO4zW560TEepLTNqQwMxTs7humUhKoBpVKvJ.hm3Dbn-mRz3TpThK?startTime=1604240384000",
        # Add more URLs here when ready
    ]

    # Create downloader from environment variables
    downloader = from_env(output_dir="recordings")

    # Download all videos
    results = downloader.download_multiple(test_urls)

    # Show results
    print("\nDetailed Results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['share_url']}")
        print(f"   Status: {result['status']}")
        if result['output_path']:
            print(f"   File: {result['output_path']}")
        if result['error']:
            print(f"   Error: {result['error']}")

    return results


if __name__ == "__main__":
    import sys

    print("="*70)
    print("ZOOM DOWNLOADER TEST")
    print("="*70)
    print()

    # Check if we want to test multiple downloads
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        test_multiple_downloads()
    else:
        test_single_download()
