#!/usr/bin/env python3
"""
Export all Zoom recordings to CSV with their unique identifiers.

This creates a catalog of all your recordings with:
- Meeting UUID (use this for reliable downloads!)
- Meeting ID
- Topic/Title
- Start Time
- Duration
- File Types

Usage:
    python list_recordings.py [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--output file.csv]

Examples:
    # List last 30 days (default)
    python list_recordings.py

    # List recordings from 2020
    python list_recordings.py --from 2020-01-01 --to 2020-12-31

    # Export to custom file
    python list_recordings.py --output my_recordings.csv
"""

import csv
import argparse
from zoom_downloader import from_env
from datetime import datetime


def export_to_csv(recordings, output_file):
    """Export recordings to CSV file"""

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow([
            'Meeting UUID',
            'Meeting ID',
            'Topic',
            'Start Time',
            'Duration (min)',
            'Recording Count',
            'Video File Types',
            'Total Size (MB)',
            'Share URL'
        ])

        # Data rows
        for rec in recordings:
            # Get video file types and total size
            video_files = [f for f in rec['recording_files'] if f['file_type'] in ['MP4', 'M4A']]
            file_types = ', '.join(set(f['file_type'] for f in video_files))
            total_size_mb = sum(f.get('file_size', 0) for f in video_files) / (1024 * 1024)

            writer.writerow([
                rec['meeting_uuid'],
                rec['meeting_id'],
                rec['topic'],
                rec['start_time'],
                rec['duration'],
                rec['recording_count'],
                file_types,
                f"{total_size_mb:.1f}",
                rec.get('share_url', '')
            ])

    print(f"\n✅ Exported {len(recordings)} recordings to: {output_file}")


def print_summary(recordings):
    """Print a summary of the recordings"""

    print(f"\n{'='*70}")
    print("RECORDINGS SUMMARY")
    print(f"{'='*70}\n")

    total_size = 0
    total_duration = 0

    for i, rec in enumerate(recordings[:10], 1):  # Show first 10
        video_files = [f for f in rec['recording_files'] if f['file_type'] in ['MP4', 'M4A']]
        size_mb = sum(f.get('file_size', 0) for f in video_files) / (1024 * 1024)

        total_size += size_mb
        total_duration += rec.get('duration', 0)

        print(f"{i}. {rec['topic']}")
        print(f"   UUID: {rec['meeting_uuid']}")
        print(f"   Date: {rec['start_time']}")
        print(f"   Duration: {rec['duration']} min | Size: {size_mb:.1f} MB")
        print()

    if len(recordings) > 10:
        # Calculate total for remaining
        for rec in recordings[10:]:
            video_files = [f for f in rec['recording_files'] if f['file_type'] in ['MP4', 'M4A']]
            size_mb = sum(f.get('file_size', 0) for f in video_files) / (1024 * 1024)
            total_size += size_mb
            total_duration += rec.get('duration', 0)

        print(f"... and {len(recordings) - 10} more recordings\n")

    print(f"{'='*70}")
    print(f"Total: {len(recordings)} recordings")
    print(f"Total Duration: {total_duration} minutes ({total_duration/60:.1f} hours)")
    print(f"Total Size: {total_size:.1f} MB ({total_size/1024:.1f} GB)")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='List and export Zoom recordings with unique identifiers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--from', dest='from_date',
                       help='Start date (YYYY-MM-DD). Default: 30 days ago')
    parser.add_argument('--to', dest='to_date',
                       help='End date (YYYY-MM-DD). Default: today')
    parser.add_argument('--output', default='zoom_recordings.csv',
                       help='Output CSV file (default: zoom_recordings.csv)')
    parser.add_argument('--max', type=int, default=1000,
                       help='Maximum recordings to fetch (default: 1000)')

    args = parser.parse_args()

    print("="*70)
    print("ZOOM RECORDINGS CATALOG")
    print("="*70)
    print()

    # Create downloader
    downloader = from_env()

    # List recordings
    recordings = downloader.list_recordings(
        from_date=args.from_date,
        to_date=args.to_date,
        max_results=args.max
    )

    if not recordings:
        print("\n⚠️  No recordings found in the specified date range")
        return

    # Print summary
    print_summary(recordings)

    # Export to CSV
    export_to_csv(recordings, args.output)

    print(f"\n💡 To download a recording, use its UUID:")
    print(f"   from zoom_downloader import from_env")
    print(f"   downloader = from_env()")
    print(f"   downloader.download_by_uuid('UUID_FROM_CSV')")


if __name__ == "__main__":
    main()
