#!/usr/bin/env python3
"""Remove all prospects from the sheet that have no contact email."""
import sys, time, pickle
sys.path.insert(0, 'tools')
import gspread
from dotenv import load_dotenv
load_dotenv()

with open('token.pickle', 'rb') as f:
    creds = pickle.load(f)
gc = gspread.authorize(creds)
ws = gc.open_by_key('1OxXcnMmYmKZEalVF3SyhkYfS5fQFl_m_6nvHHRHKkW8').worksheet('Prospects')

all_rows = ws.get_all_values()
header = all_rows[0]
email_col = 2  # Column C (0-indexed = 2), Contact Email

# Find rows to delete (bottom to top to preserve row numbers)
to_delete = []
for i, row in enumerate(all_rows[1:], start=2):  # start=2 because row 1 is header
    email = row[email_col].strip() if len(row) > email_col else ''
    company = row[0].strip()
    if not email:
        to_delete.append((i, company))

if not to_delete:
    print('No prospects without emails found.')
else:
    print(f'Found {len(to_delete)} prospects without emails:')
    for row_num, company in to_delete:
        print(f'  Row {row_num}: {company}')

    # Delete from bottom to top so row numbers stay valid
    for row_num, company in reversed(to_delete):
        ws.delete_rows(row_num)
        print(f'DELETED: {company}')
        time.sleep(0.5)

    print(f'\nDone. Removed {len(to_delete)} prospects.')
