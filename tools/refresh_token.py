#!/usr/bin/env python3
"""Refresh Google OAuth token only. Does not create or modify any spreadsheet."""
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

with open('token.pickle', 'wb') as f:
    pickle.dump(creds, f)

print('Done. token.pickle saved.')
