#!/usr/bin/env python3
"""
Batch download recordings from a CSV file with share links.

This script handles CSV files in the format:
Name of the Meeting,Email,Meeting ID,Date,Time,Meeting Type,Teacher,Share Link

Usage:
    python batch_download_from_csv.py input.csv
    python batch_download_from_csv.py input.csv --output-dir my_downloads
"""

import csv
import argparse
import sys
from pathlib import Path
from zoom_downloader import from_env


def parse_share_link(link):
    """Extract clean share link from CSV (handles multi-line passcode format)"""
    # Remove passcode lines and extra whitespace
    link = link.split('\n')[0].strip()
    # Remove "Passcode: " suffix if present
    if 'Passcode:' in link:
        link = link.split('Passcode:')[0].strip()
    return link


def download_from_csv(csv_file, output_dir="recordings", skip_existing=True):
    """
    Download all recordings listed in a CSV file.

    Args:
        csv_file: Path to CSV file with share links
        output_dir: Directory to save downloads
        skip_existing: Skip downloads if file already exists
    """

    # Read the CSV
    recordings = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Try to detect if file has headers
        sample = f.read(1024)
        f.seek(0)
        has_header = 'Share Link' in sample or 'Meeting' in sample

        reader = csv.DictReader(f) if has_header else csv.reader(f)

        for row in reader:
            if isinstance(row, dict):
                # DictReader - use column names
                share_link = row.get('Share Link', '').strip()
                name = row.get('Name of the Meeting', 'Unknown').strip()
                date = row.get('Date', '').strip()
                teacher = row.get('Teacher', '').strip()
            else:
                # Regular reader - use indices
                if len(row) < 8:
                    continue
                name = row[0].strip()
                date = row[3].strip()
                teacher = row[6].strip()
                share_link = row[7].strip()

            # Skip empty rows or rows without share links
            if not share_link or not name:
                continue

            # Clean up the share link
            share_link = parse_share_link(share_link)

            recordings.append({
                'name': name,
                'date': date,
                'teacher': teacher,
                'share_link': share_link
            })

    if not recordings:
        print("❌ No recordings found in CSV file")
        return

    print(f"{'='*70}")
    print(f"BATCH DOWNLOAD FROM CSV")
    print(f"{'='*70}")
    print(f"Found {len(recordings)} recordings to download\n")

    # Create downloader
    downloader = from_env(output_dir=output_dir)

    # Track results
    successful = 0
    failed = 0
    skipped = 0

    # Download each recording
    for i, rec in enumerate(recordings, 1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(recordings)}] {rec['name']}")
        print(f"Date: {rec['date']} | Teacher: {rec['teacher']}")
        print(f"{'='*70}")

        # Generate a safe filename from the metadata
        safe_name = "".join(c for c in rec['name'] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        safe_date = rec['date'].replace(',', '').replace(' ', '_')
        custom_filename = f"{safe_date}_{safe_name}"

        # Check if file already exists
        output_path = Path(output_dir) / f"{custom_filename}.mp4"
        if skip_existing and output_path.exists():
            print(f"⏭️  Skipping - file already exists: {output_path}")
            skipped += 1
            continue

        try:
            # Download the recording
            result = downloader.download_from_share_url(
                rec['share_link'],
                custom_filename=custom_filename
            )

            if result:
                print(f"✅ Successfully downloaded!")
                successful += 1
            else:
                print(f"❌ Failed to download")
                failed += 1

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            failed += 1

        # Brief pause between downloads
        if i < len(recordings):
            import time
            time.sleep(2)

    # Print summary
    print(f"\n{'='*70}")
    print("DOWNLOAD SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📊 Total: {len(recordings)}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Batch download Zoom recordings from CSV file with share links',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('csv_file', help='CSV file with recording information')
    parser.add_argument('--output-dir', default='recordings',
                       help='Output directory (default: recordings)')
    parser.add_argument('--no-skip', action='store_true',
                       help='Re-download even if file exists')

    args = parser.parse_args()

    if not Path(args.csv_file).exists():
        print(f"❌ Error: CSV file not found: {args.csv_file}")
        sys.exit(1)

    download_from_csv(
        args.csv_file,
        output_dir=args.output_dir,
        skip_existing=not args.no_skip
    )


if __name__ == "__main__":
    main()
