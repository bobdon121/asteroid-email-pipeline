#!/usr/bin/env python3
"""
Google Sheet Setup - Creates tracking spreadsheet for cold email campaign

Creates a Google Sheet with multiple tabs:
1. Prospects - Main tracking tab for all companies and email status
2. Campaign Stats - Analytics and performance metrics
3. Templates - Template performance tracking
4. Send Log - Detailed audit trail of every email sent
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import time
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.pickle"

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']


def get_credentials():
    """
    Get Google API credentials using OAuth2 flow.

    Returns:
        Credentials object
    """
    creds = None

    # Check if we have saved credentials
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {CREDENTIALS_FILE}\n"
                    "Please download credentials.json from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/\n"
                    "2. Create a project\n"
                    "3. Enable Google Sheets API\n"
                    "4. Create OAuth 2.0 credentials\n"
                    "5. Download and save as credentials.json"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next time
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def create_prospects_sheet(worksheet):
    """
    Set up the Prospects tab with headers and formatting.

    Column mapping for Asteroid.ai pipeline:
      A: Company Name       B: Website            C: Contact Email
      D: Contact Name       E: Contact Title       F: Industry/Description
      G: Location           H: (spare)             I: (spare)
      J: Research Data      K: Email Subject       L: Email Body
      M: Template Used      N: Status

    Args:
        worksheet: gspread worksheet object
    """
    headers = [
        "Company Name",          # A — required
        "Website",               # B — required
        "Contact Email",         # C — required
        "Contact Name",          # D — required
        "Contact Title",         # E — e.g. "VP Operations"
        "Industry / Description", # F — healthcare sub-vertical or short description
        "Location",              # G — city/country
        "",                      # H — spare
        "",                      # I — spare
        "Research Data",         # J — JSON written by research_company.py
        "Email Subject",         # K — written by generate_email.py
        "Email Body",            # L — written by generate_email.py
        "Template Used",         # M — written by generate_email.py
        "Status",                # N — Pending / Ready / Disqualified / Sent
        "Sent Date",             # O
        "Replied",               # P
        "Replied At",            # Q
        "Notes",                 # R
    ]

    worksheet.insert_row(headers, 1)

    worksheet.format('A1:R1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    worksheet.freeze(rows=1)

    # Example row — delete after adding real prospects
    example = [
        "Thyme Care",
        "thymecare.com",
        "contact@thymecare.com",
        "Jane Smith",
        "VP Operations",
        "Oncology navigation / RCM",
        "Nashville, TN",
        "",
        "",
        "",   # Research Data — filled by pipeline
        "",   # Email Subject — filled by pipeline
        "",   # Email Body — filled by pipeline
        "",   # Template Used — filled by pipeline
        "Pending",
        "",
        "",
        "",
        "Example row — replace with real prospects",
    ]
    worksheet.insert_row(example, 2)


def create_stats_sheet(worksheet):
    """
    Set up the Campaign Stats tab with metrics tracking.

    Args:
        worksheet: gspread worksheet object
    """
    # Headers and structure
    content = [
        ["Campaign Statistics", ""],
        [""],
        ["Metric", "Value"],
        ["Total Emails Sent", "=COUNTIF(Prospects!N:N,\"Sent\")"],
        ["Total Opened", "=COUNTIF(Prospects!P:P,\"Yes\")"],
        ["Total Replied", "=COUNTIF(Prospects!R:R,\"Yes\")"],
        ["Total Bounced", "=COUNTIF(Prospects!N:N,\"Bounced\")"],
        ["Total Unsubscribed", "=COUNTIF(Prospects!U:U,\"Yes\")"],
        [""],
        ["Open Rate (%)", "=IF(B4=0,0,ROUND(B5/B4*100,1))"],
        ["Reply Rate (%)", "=IF(B4=0,0,ROUND(B6/B4*100,1))"],
        ["Bounce Rate (%)", "=IF(B4=0,0,ROUND(B7/B4*100,1))"],
        [""],
        ["Current Week", ""],
        ["Emails This Week", ""],
        [""],
        ["Best Performing Template", ""],
        [""],
        ["Daily Send History", ""],
        ["Date", "Emails Sent", "Opened", "Replied"],
    ]

    for i, row in enumerate(content, 1):
        worksheet.insert_row(row, i)

    # Format headers
    worksheet.format('A1:B1', {
        'textFormat': {'bold': True, 'fontSize': 14},
    })
    worksheet.format('A3:B3', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })


def create_templates_sheet(worksheet):
    """
    Set up the Templates tab for tracking template performance.

    Args:
        worksheet: gspread worksheet object
    """
    headers = [
        "Template Name",
        "Times Used",
        "Opens",
        "Replies",
        "Open Rate (%)",
        "Reply Rate (%)"
    ]

    worksheet.insert_row(headers, 1)

    # Format headers
    worksheet.format('A1:F1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })


def create_send_log_sheet(worksheet):
    """
    Set up the Send Log tab for detailed audit trail.

    Args:
        worksheet: gspread worksheet object
    """
    headers = [
        "Timestamp",
        "Company Name",
        "Website",
        "Contact Email",
        "Contact Name",
        "Founder/CEO",
        "Founder LinkedIn",
        "Company LinkedIn",
        "Industry",
        "Company Size",
        "Email Subject",
        "Template Used",
        "Send Status",
        "SMTP Message ID",
        "Sent From",
        "Campaign Day",
        "Week #"
    ]

    worksheet.insert_row(headers, 1)

    # Format headers
    worksheet.format('A1:Q1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 0.85}
    })

    # Freeze header row
    worksheet.freeze(rows=1)


def create_tracking_sheet(sheet_name="Asteroid.ai Outreach Tracker"):
    """
    Create a new Google Sheet for tracking the cold email campaign.

    Args:
        sheet_name: Name for the new spreadsheet

    Returns:
        dict: {
            'sheet_id': str,
            'sheet_url': str,
            'sheet_name': str
        }
    """
    print("Authenticating with Google Sheets...")
    creds = get_credentials()
    client = gspread.authorize(creds)

    print(f"Creating spreadsheet: {sheet_name}...")
    spreadsheet = client.create(sheet_name)

    # Get the default sheet and rename it
    prospects_sheet = spreadsheet.sheet1
    prospects_sheet.update_title("Prospects")

    print("Setting up Prospects tab...")
    create_prospects_sheet(prospects_sheet)
    time.sleep(5)

    print("Creating Campaign Stats tab...")
    stats_sheet = spreadsheet.add_worksheet("Campaign Stats", 100, 10)
    create_stats_sheet(stats_sheet)
    time.sleep(5)

    print("Creating Templates tab...")
    templates_sheet = spreadsheet.add_worksheet("Templates", 50, 6)
    create_templates_sheet(templates_sheet)
    time.sleep(5)

    print("Creating Send Log tab...")
    send_log_sheet = spreadsheet.add_worksheet("Send Log", 500, 17)
    create_send_log_sheet(send_log_sheet)

    # Share with anyone (or specific emails)
    # spreadsheet.share('user@example.com', perm_type='user', role='writer')

    result = {
        'sheet_id': spreadsheet.id,
        'sheet_url': spreadsheet.url,
        'sheet_name': sheet_name
    }

    print(f"\nGoogle Sheet created successfully!")
    print(f"   Name: {sheet_name}")
    print(f"   URL: {result['sheet_url']}")
    print(f"   ID: {result['sheet_id']}")

    return result


def update_config_with_sheet_id(sheet_id):
    """
    Update the config file with the Google Sheet ID.

    Args:
        sheet_id: Google Sheet ID
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        config['google_sheet_id'] = sheet_id

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"Updated config file with Sheet ID")


def main():
    """CLI interface for creating tracking sheet."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create Google Sheet for cold email tracking"
    )
    parser.add_argument(
        '--name', '-n',
        default="Asteroid.ai Outreach Tracker",
        help="Name for the spreadsheet"
    )
    parser.add_argument(
        '--update-config',
        action='store_true',
        help="Update config file with Sheet ID"
    )

    args = parser.parse_args()

    try:
        result = create_tracking_sheet(args.name)

        if args.update_config:
            update_config_with_sheet_id(result['sheet_id'])

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
