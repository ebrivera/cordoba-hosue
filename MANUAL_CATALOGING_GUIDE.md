# Guide for Manual Video Cataloging

## IMPORTANT: You Probably Don't Need to Do This Manually!

Instead of manually writing down videos, ask your technical contact to run:
```bash
python list_recordings.py --from 2020-01-01 --to 2024-12-31
```

This will **automatically export ALL videos** to a CSV file in seconds. Much faster and more accurate than manual work!

---

## If You MUST Catalog Manually

If you're looking at the Zoom web interface and need to write down video information, here's what to collect:

### Required Information (Must Have)

1. **Share Link** ⭐ **MOST IMPORTANT** - This is the unique identifier
   - Where to find it: Click the video → Click "Share" button → Copy the link
   - Example: `https://us02web.zoom.us/rec/share/K87Fx1wSLflLf6-jeKItz...`
   - ✅ Share links are UNIQUE per recording - this is your best identifier!

2. **Meeting Name/Topic**
   - Example: "Ibn Battuta Sunday Class"
   - Note: Names can repeat, but they're good for human reference

3. **Date & Time**
   - When the recording was made
   - Example: "Mar 22, 2020, 10:29 AM"

### Optional Information (Nice to Have)

4. **Meeting ID**
   - The numeric ID shown for the meeting
   - Example: 871 438 946
   - ⚠️ WARNING: This ID is often REUSED for recurring meetings, so it's not unique!

5. **Teacher/Host Name**
   - Who conducted the session
   - Example: "Marwa Elshamy"

6. **Email/Account**
   - Which Zoom account owns this recording
   - Example: "cordobahouseschool1@gmail.com"
   - Important: All recordings must be from the SAME account to download them

### CSV Format

Create a CSV file with these columns:

```csv
Name of the Meeting,Email,Meeting ID,Date,Time,Meeting Type,Teacher,Share Link
Ibn Battuta Sunday Class,cordobahouseschool1@gmail.com,871438946,Mar 22 2020,10:29 AM,Classroom Session,Marwa Elshamy,https://us02web.zoom.us/rec/share/K87Fx1wSLflLf6-jeKItz...
```

### Important Notes

1. **Share Link is the KEY** - Don't skip this! It's the most reliable identifier.

2. **Meeting IDs are NOT unique** - The same meeting ID is used for all recordings of a recurring meeting. Don't rely on Meeting ID alone!

3. **All recordings must be from the same account** - Make sure the email/account is consistent.

4. **Copy the FULL share link** - Include everything, even the `?startTime=` parameter if present.

5. **Passcodes** - If a recording has a passcode, you can write it on a new line or after the link, but the download script won't need it (API access bypasses passcodes).

### Example Data

```csv
Name of the Meeting,Email,Meeting ID,Date,Time,Meeting Type,Teacher,Share Link
Ibn Battuta 1 and 2,cordobahouseschool1@gmail.com,982046018,Mar 22 2020,10:29 AM,Classroom Session,Marwa Elshamy,https://us02web.zoom.us/rec/share/AtdgqzZZVDaxgQrZ9zi8LxDBmkmR9zAywXyDr-BmAusL5MqYgycZw2A3gBwhFVwl.IMF_KocBJaohnImb?startTime=1584887394000
Ibn Battuta Sunday Class,cordobahouseschool1@gmail.com,871438946,Mar 29 2020,9:50 AM,Classroom Session,Marwa Elshamy,https://us02web.zoom.us/rec/share/CcnXWexSvNLQKq_HIr0WQMSiTmGrx4SqwTehfSnycMP_qiNlN1RVPeQEOo4U4Xk.WbC-mYA8WJd-lE9O
```

### After Creating Your CSV

Send the CSV file to your technical contact. They can then:

**Option 1: Download directly from your CSV**
```bash
python batch_download_from_csv.py your_recordings.csv
```

**Option 2: Match with API to get UUIDs (more reliable)**
```bash
python match_csv_to_uuids.py your_recordings.csv --from 2020-01-01 --to 2024-12-31
```

---

## Troubleshooting

**Q: The Meeting ID is the same for multiple videos. Is this wrong?**
A: No, this is normal! Recurring meetings use the same Meeting ID. The Share Link is what makes each recording unique.

**Q: Should I include passcodes?**
A: Optional. The download scripts use API access which bypasses passcodes.

**Q: Some recordings are missing from Zoom. Why?**
A: They may have been:
- Deleted from cloud storage
- Moved to trash
- From a different Zoom account
- Set to expire after a certain time

**Q: How do I get the share link?**
A: In Zoom web portal:
1. Go to Recordings
2. Click on a recording
3. Click the "Share" button
4. Copy the share link

**Q: Is there a faster way?**
A: YES! Ask your technical contact to run `python list_recordings.py` instead of doing this manually!
