#!/usr/bin/env python3
"""
Complete Pipeline: Download → Transcribe → Segment

Test with ONE video to verify the full pipeline works.

Setup:
    1. Add to .env:
       OPENAI_API_KEY=your_openai_key
       ANTHROPIC_API_KEY=your_anthropic_key

    2. Run: python pipeline_one_video.py

This will:
1. Download the test video from your CSV
2. Transcribe it using Whisper API
3. Segment it into 5 sections using Claude
"""

from pathlib import Path
from zoom_downloader import from_env
from transcriber import transcribe_video
from segmenter import segment_video
from structured_export import export_video_segmentation

# Test video from your CSV
TEST_SHARE_URL = "https://us02web.zoom.us/rec/share/AtdgqzZZVDaxgQrZ9zi8LxDBmkmR9zAywXyDr-BmAusL5MqYgycZw2A3gBwhFVwl.IMF_KocBJaohnImb?startTime=1584887394000"
TEST_NAME = "Ibn Batuta 1 and 2"
TEST_DATE = "Mar_22_2020"


def run_pipeline():
    """Run the complete pipeline on one video"""

    print("="*70)
    print("COMPLETE VIDEO PROCESSING PIPELINE")
    print("="*70)
    print(f"Video: {TEST_NAME}")
    print(f"Date: {TEST_DATE}")
    print("="*70)
    print()

    # Create output directories
    recordings_dir = Path("recordings")
    transcripts_dir = Path("transcripts")
    segments_dir = Path("segments")

    for d in [recordings_dir, transcripts_dir, segments_dir]:
        d.mkdir(exist_ok=True)

    # ========================================
    # STEP 1: Download Video
    # ========================================
    print("\n" + "="*70)
    print("STEP 1: DOWNLOAD VIDEO")
    print("="*70)

    downloader = from_env(output_dir=str(recordings_dir))
    custom_filename = f"{TEST_DATE}_{TEST_NAME.replace(' ', '_')}"

    video_path = downloader.download_from_share_url(
        TEST_SHARE_URL,
        custom_filename=custom_filename
    )

    if not video_path:
        print("\n❌ Pipeline failed: Could not download video")
        return None

    print(f"\n✅ Step 1 Complete: Video downloaded to {video_path}")

    # ========================================
    # STEP 2: Transcribe Video
    # ========================================
    print("\n" + "="*70)
    print("STEP 2: TRANSCRIBE VIDEO")
    print("="*70)

    try:
        transcript = transcribe_video(video_path, output_dir=transcripts_dir)
        print(f"\n✅ Step 2 Complete: Transcript created")
        print(f"   Duration: {transcript['duration']:.1f} seconds")
        print(f"   Segments: {len(transcript['segments'])}")
    except Exception as e:
        print(f"\n❌ Pipeline failed during transcription: {str(e)}")
        print(f"\n💡 Make sure you have OPENAI_API_KEY in your .env file")
        return None

    # ========================================
    # STEP 3: Segment Transcript
    # ========================================
    print("\n" + "="*70)
    print("STEP 3: SEGMENT INTO SECTIONS")
    print("="*70)

    try:
        transcript_json = transcripts_dir / f"{custom_filename}_transcript.json"
        segmentation = segment_video(transcript_json, output_dir=segments_dir)

        print(f"\n✅ Step 3 Complete: Video segmented")

        # Show the segments
        if "sections" in segmentation and segmentation["sections"]:
            print(f"\n📋 Found {len(segmentation['sections'])} sections:")
            for i, section in enumerate(segmentation['sections'], 1):
                print(f"\n{i}. {section['type']}")
                print(f"   Time: {section['start_time']} - {section['end_time']}")
                print(f"   {section['summary'][:80]}...")
        else:
            print("\n⚠️  No sections identified (check segmentation file)")

    except Exception as e:
        print(f"\n❌ Pipeline failed during segmentation: {str(e)}")
        print(f"\n💡 Make sure you have ANTHROPIC_API_KEY in your .env file")
        return None

    # ========================================
    # STEP 4: Export to Structured Format
    # ========================================
    print("\n" + "="*70)
    print("STEP 4: EXPORT TO STRUCTURED FORMAT")
    print("="*70)

    structured_dir = Path("structured_output")
    structured_dir.mkdir(exist_ok=True)

    # Calculate duration in minutes
    duration_minutes = transcript.get('duration', 0) / 60

    # Export to CSV and JSON
    export_video_segmentation(
        segmentation=segmentation,
        video_name=TEST_NAME,
        date=TEST_DATE,
        teacher="Unknown",  # Would come from CSV in batch mode
        duration_minutes=duration_minutes,
        output_dir=structured_dir
    )

    print(f"\n✅ Step 4 Complete: Structured data exported")

    # ========================================
    # PIPELINE COMPLETE
    # ========================================
    print("\n" + "="*70)
    print("🎉 PIPELINE COMPLETE!")
    print("="*70)
    print(f"\nOutput files:")
    print(f"  Video:        {video_path}")
    print(f"  Transcript:   {transcripts_dir / f'{custom_filename}_transcript.json'}")
    print(f"  Transcript:   {transcripts_dir / f'{custom_filename}_transcript.txt'}")
    print(f"  Segmentation: {segments_dir / f'{custom_filename}_segments.json'}")
    print(f"  Segmentation: {segments_dir / f'{custom_filename}_segments.txt'}")
    print(f"  Structured:   {structured_dir / f'{custom_filename}_structured.json'}")
    print(f"  Master CSV:   {structured_dir / 'all_videos_structured.csv'}")
    print()

    return {
        "video_path": video_path,
        "transcript": transcript,
        "segmentation": segmentation
    }


if __name__ == "__main__":
    print("""
⚠️  REQUIREMENTS CHECK:

    Make sure your .env file has:
    - ZOOM_ACCOUNT_ID
    - ZOOM_CLIENT_ID
    - ZOOM_CLIENT_SECRET
    - ZOOM_USER_ID
    - OPENAI_API_KEY         ← For transcription
    - ANTHROPIC_API_KEY      ← For segmentation

    Install required packages:
    pip install openai anthropic --break-system-packages

""")

    input("Press Enter to start the pipeline...")

    result = run_pipeline()

    if result:
        print("\n✅ SUCCESS! Check the output files above.")
        print("\nNext steps:")
        print("  1. Review the segmentation to see if it's accurate")
        print("  2. If good, you can run this on all videos in your CSV")
        print("  3. Use batch_pipeline_from_csv.py for bulk processing")
    else:
        print("\n❌ Pipeline failed. Check the errors above.")
