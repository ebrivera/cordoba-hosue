#!/usr/bin/env python3
"""
Match manually cataloged recordings with API recordings to get UUIDs.

This helps you:
1. Take the CSV your team manually created (with share links)
2. Match it against Zoom API recordings (which have UUIDs)
3. Output a new CSV with UUIDs added

Then you can use UUIDs for reliable downloads!

Usage:
    python match_csv_to_uuids.py manual_recordings.csv --from 2020-01-01 --to 2021-12-31
"""

import csv
import argparse
from datetime import datetime
from pathlib import Path
from zoom_downloader import from_env


def parse_date(date_str):
    """Parse various date formats from CSV"""
    date_str = date_str.strip().replace(',', '')

    # Try different formats
    formats = [
        '%b %d %Y',      # Mar 22 2020
        '%B %d %Y',      # March 22 2020
        '%m/%d/%Y',      # 03/22/2020
        '%Y-%m-%d',      # 2020-03-22
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue

    return None


def match_recordings(manual_csv, from_date, to_date):
    """Match manual CSV with API recordings"""

    # Read manual CSV
    print("📄 Reading manual CSV...")
    manual_recordings = []

    with open(manual_csv, 'r', encoding='utf-8') as f:
        sample = f.read(1024)
        f.seek(0)
        has_header = 'Share Link' in sample

        reader = csv.DictReader(f) if has_header else csv.reader(f)

        for row in reader:
            if isinstance(row, dict):
                name = row.get('Name of the Meeting', '').strip()
                date_str = row.get('Date', '').strip()
                share_link = row.get('Share Link', '').strip()
                meeting_id = row.get('Meeting ID', '').strip()
            else:
                if len(row) < 8:
                    continue
                name = row[0].strip()
                meeting_id = row[2].strip()
                date_str = row[3].strip()
                share_link = row[7].strip()

            if not name or not share_link:
                continue

            # Parse date
            parsed_date = parse_date(date_str)

            manual_recordings.append({
                'name': name,
                'meeting_id': meeting_id,
                'date_str': date_str,
                'date': parsed_date,
                'share_link': share_link.split('\n')[0].strip()
            })

    print(f"   Found {len(manual_recordings)} manually cataloged recordings\n")

    # Fetch API recordings
    print("🔍 Fetching recordings from Zoom API...")
    downloader = from_env()
    api_recordings = downloader.list_recordings(
        from_date=from_date,
        to_date=to_date,
        max_results=1000
    )

    print(f"   Found {len(api_recordings)} recordings in API\n")

    # Match them
    print("🔗 Matching recordings...")
    matched = []
    unmatched = []

    for manual_rec in manual_recordings:
        match_found = False

        for api_rec in api_recordings:
            # Strategy 1: Match by share URL
            if manual_rec['share_link'] and api_rec.get('share_url'):
                # Extract recording ID from both
                manual_id = manual_rec['share_link'].split('/rec/share/')[-1].split('?')[0].split('/')[0]
                api_id = api_rec['share_url'].split('/rec/share/')[-1].split('?')[0].split('/')[0] if '/rec/share/' in api_rec['share_url'] else ''

                if manual_id and api_id and manual_id in api_id:
                    matched.append({
                        **manual_rec,
                        'uuid': api_rec['meeting_uuid'],
                        'api_topic': api_rec['topic'],
                        'api_start_time': api_rec['start_time'],
                        'match_method': 'share_url'
                    })
                    match_found = True
                    break

            # Strategy 2: Match by date and name similarity
            if manual_rec['date'] and api_rec['start_time']:
                api_date = datetime.fromisoformat(api_rec['start_time'].replace('Z', '+00:00'))
                date_diff = abs((manual_rec['date'] - api_date.replace(tzinfo=None)).total_seconds())

                # Within same day and similar name
                if date_diff < 86400:  # 24 hours
                    manual_name_lower = manual_rec['name'].lower()
                    api_name_lower = api_rec['topic'].lower()

                    # Check for name similarity
                    if (manual_name_lower in api_name_lower or
                        api_name_lower in manual_name_lower or
                        manual_name_lower[:20] == api_name_lower[:20]):

                        matched.append({
                            **manual_rec,
                            'uuid': api_rec['meeting_uuid'],
                            'api_topic': api_rec['topic'],
                            'api_start_time': api_rec['start_time'],
                            'match_method': 'date_and_name'
                        })
                        match_found = True
                        break

        if not match_found:
            unmatched.append(manual_rec)

    print(f"   ✅ Matched: {len(matched)}")
    print(f"   ❌ Unmatched: {len(unmatched)}\n")

    return matched, unmatched


def export_results(matched, unmatched, output_file):
    """Export results to CSV"""

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'Name',
            'Date',
            'Meeting ID',
            'Share Link',
            'Meeting UUID',
            'API Topic',
            'API Start Time',
            'Match Method',
            'Status'
        ])

        # Matched recordings
        for rec in matched:
            writer.writerow([
                rec['name'],
                rec['date_str'],
                rec['meeting_id'],
                rec['share_link'],
                rec['uuid'],
                rec['api_topic'],
                rec['api_start_time'],
                rec['match_method'],
                'MATCHED'
            ])

        # Unmatched recordings
        for rec in unmatched:
            writer.writerow([
                rec['name'],
                rec['date_str'],
                rec['meeting_id'],
                rec['share_link'],
                'NOT_FOUND',
                '',
                '',
                '',
                'UNMATCHED'
            ])

    print(f"✅ Results exported to: {output_file}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Match manual CSV with API recordings to get UUIDs'
    )
    parser.add_argument('csv_file', help='Manually created CSV file')
    parser.add_argument('--from', dest='from_date', required=True,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to', dest='to_date', required=True,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', default='matched_recordings.csv',
                       help='Output CSV file (default: matched_recordings.csv)')

    args = parser.parse_args()

    if not Path(args.csv_file).exists():
        print(f"❌ Error: File not found: {args.csv_file}")
        return

    print("="*70)
    print("MATCH MANUAL CSV WITH API RECORDINGS")
    print("="*70)
    print()

    matched, unmatched = match_recordings(
        args.csv_file,
        args.from_date,
        args.to_date
    )

    export_results(matched, unmatched, args.output)

    print("💡 Next steps:")
    print(f"   1. Open {args.output} to see matched recordings with UUIDs")
    print(f"   2. For matched recordings, you can download by UUID:")
    print(f"      downloader.download_by_uuid('UUID_FROM_CSV')")
    print(f"   3. For unmatched recordings, try downloading by share link")


if __name__ == "__main__":
    main()
