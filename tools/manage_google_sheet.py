#!/usr/bin/env python3
"""
Google Sheet Manager - CRUD operations for cold email campaign tracking

Provides functions to:
- Read companies by status
- Update research data (including founder/LinkedIn info)
- Update email content
- Mark emails as sent
- Log send events to Send Log tab
- Track opens and replies
- Get email counts

Column mapping (Prospects tab):
  A=1: Company Name    F=6: Founder/CEO      K=11: Email Subject   P=16: Opened       U=21: Unsubscribed
  B=2: Website         G=7: Founder LinkedIn  L=12: Email Body      Q=17: Opened At    V=22: Bounce Reason
  C=3: Contact Email   H=8: Company LinkedIn  M=13: Template Used   R=18: Replied      W=23: Week #
  D=4: Contact Name    I=9: Company Size      N=14: Status          S=19: Replied At   X=24: Campaign Day
  E=5: Industry        J=10: Research Data    O=15: Sent Date       T=20: Reply Content Y=25: Notes
  Z=26: Description
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import gspread
import pickle

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"
TOKEN_FILE = PROJECT_ROOT / "token.pickle"
LOG_DIR = PROJECT_ROOT / ".tmp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Column indices for Prospects tab
COL = {
    'company_name': 1, 'website': 2, 'contact_email': 3, 'contact_name': 4,
    'industry': 5, 'founder_ceo': 6, 'founder_linkedin': 7,
    'company_linkedin': 8, 'company_size': 9, 'research_data': 10,
    'email_subject': 11, 'email_body': 12, 'template_used': 13,
    'status': 14, 'sent_date': 15, 'opened': 16, 'opened_at': 17,
    'replied': 18, 'replied_at': 19, 'reply_content': 20,
    'unsubscribed': 21, 'bounce_reason': 22, 'week': 23,
    'campaign_day': 24, 'notes': 25, 'description': 26
}


def get_sheet_client():
    """Get authenticated gspread client."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            "No Google Sheets credentials found. "
            "Please run setup_google_sheet.py first to authenticate."
        )
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    return gspread.authorize(creds)


def get_spreadsheet():
    """Get the tracking spreadsheet object."""
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    sheet_id = config.get('google_sheet_id')
    if not sheet_id:
        raise ValueError("No Google Sheet ID in config. Run setup_automation.py first.")
    client = get_sheet_client()
    return client.open_by_key(sheet_id)


def get_prospects_sheet():
    """Get the Prospects worksheet."""
    return get_spreadsheet().worksheet("Prospects")


def get_send_log_sheet():
    """Get the Send Log worksheet."""
    return get_spreadsheet().worksheet("Send Log")


# ─── READ OPERATIONS ────────────────────────────────────────────────────────────

def get_pending_companies(limit=None, status_filter="Pending"):
    """Get companies by status. Returns list of dicts."""
    sheet = get_prospects_sheet()
    all_records = sheet.get_all_records()
    filtered = [r for r in all_records if r.get('Status') == status_filter]
    if limit:
        filtered = filtered[:limit]
    return filtered


def count_sent_today():
    """Count emails sent today."""
    sheet = get_prospects_sheet()
    all_records = sheet.get_all_records()
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for r in all_records if str(r.get('Sent Date', '')).startswith(today))


def count_sent_this_week():
    """Count emails sent this calendar week."""
    sheet = get_prospects_sheet()
    all_records = sheet.get_all_records()
    current_week = datetime.now().isocalendar()[1]
    count = 0
    for record in all_records:
        sent_date = str(record.get('Sent Date', ''))
        if sent_date:
            try:
                sent_dt = datetime.strptime(sent_date.split()[0], "%Y-%m-%d")
                if sent_dt.isocalendar()[1] == current_week:
                    count += 1
            except ValueError:
                pass
    return count


# ─── WRITE OPERATIONS ───────────────────────────────────────────────────────────

def add_company(company_name, website, contact_email, contact_name="", industry="", description=""):
    """Add a new company to track."""
    sheet = get_prospects_sheet()
    new_row = [
        company_name, website, contact_email, contact_name, industry,
        "", "", "", "",       # Founder/CEO, Founder LinkedIn, Company LinkedIn, Size
        "",                   # Research Data
        "", "", "",           # Subject, Body, Template
        "Pending",            # Status
        "",                   # Sent Date
        "No", "",             # Opened, Opened At
        "No", "", "",         # Replied, Replied At, Reply Content
        "No", "",             # Unsubscribed, Bounce Reason
        "", "",               # Week, Campaign Day
        "",                   # Notes
        description           # Description
    ]
    sheet.append_row(new_row)
    return True


def update_research_data(company_name, research_data):
    """Update research data and founder/LinkedIn info for a company."""
    sheet = get_prospects_sheet()
    cell = sheet.find(company_name)
    if not cell:
        print(f"Warning: Company '{company_name}' not found in sheet")
        return False

    row = cell.row
    research_json = json.dumps(research_data) if isinstance(research_data, dict) else str(research_data)

    # Update all research-related columns
    updates = {
        COL['research_data']: research_json,
        COL['status']: "Researched"
    }

    # Extract structured fields if research_data is a dict
    if isinstance(research_data, dict):
        if research_data.get('founder_ceo'):
            updates[COL['founder_ceo']] = research_data['founder_ceo']
        if research_data.get('founder_linkedin'):
            updates[COL['founder_linkedin']] = research_data['founder_linkedin']
        if research_data.get('company_linkedin'):
            updates[COL['company_linkedin']] = research_data['company_linkedin']
        if research_data.get('company_size'):
            updates[COL['company_size']] = research_data['company_size']

    for col_idx, value in updates.items():
        sheet.update_cell(row, col_idx, value)

    return True


def update_email_content(company_name, subject, body, template_name):
    """Update generated email content for a company."""
    sheet = get_prospects_sheet()
    cell = sheet.find(company_name)
    if not cell:
        print(f"Warning: Company '{company_name}' not found in sheet")
        return False

    row = cell.row
    sheet.update_cell(row, COL['email_subject'], subject)
    sheet.update_cell(row, COL['email_body'], body)
    sheet.update_cell(row, COL['template_used'], template_name)
    sheet.update_cell(row, COL['status'], "Ready")
    return True


def update_status(company_name, status):
    """Update the status of a company in Prospects tab."""
    sheet = get_prospects_sheet()
    cell = sheet.find(company_name)
    if not cell:
        print(f"Warning: Company '{company_name}' not found in sheet")
        return False
    row = cell.row
    sheet.update_cell(row, COL['status'], status)
    return True


def mark_as_sent(company_name, week_number, campaign_day):
    """Mark an email as sent in Prospects tab."""
    sheet = get_prospects_sheet()
    cell = sheet.find(company_name)
    if not cell:
        print(f"Warning: Company '{company_name}' not found in sheet")
        return False

    row = cell.row
    sent_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update_cell(row, COL['status'], "Sent")
    sheet.update_cell(row, COL['sent_date'], sent_time)
    sheet.update_cell(row, COL['week'], week_number)
    sheet.update_cell(row, COL['campaign_day'], campaign_day)
    return True


def mark_as_opened(company_name):
    """Mark an email as opened."""
    sheet = get_prospects_sheet()
    cell = sheet.find(company_name)
    if not cell:
        return False
    row = cell.row
    sheet.update_cell(row, COL['opened'], "Yes")
    sheet.update_cell(row, COL['opened_at'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return True


def mark_as_replied(company_name, reply_content):
    """Mark an email as replied with content."""
    sheet = get_prospects_sheet()
    cell = sheet.find(company_name)
    if not cell:
        return False
    row = cell.row
    sheet.update_cell(row, COL['replied'], "Yes")
    sheet.update_cell(row, COL['replied_at'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sheet.update_cell(row, COL['reply_content'], str(reply_content)[:500])
    return True


# ─── SEND LOG OPERATIONS ────────────────────────────────────────────────────────

def log_send_event(company_data, email_subject, template_name, send_status,
                   message_id="", campaign_day=0, week_number=0, sent_from=""):
    """
    Log a complete send event to the Send Log tab.

    Args:
        company_data: Dict with all company fields from Prospects row
        email_subject: Subject line of the sent email
        template_name: Template used
        send_status: "Success" or "Failed"
        message_id: SMTP message ID
        campaign_day: Campaign day number
        week_number: Campaign week number
        sent_from: Email address of the SMTP account used to send
    """
    log_sheet = get_send_log_sheet()

    log_row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        company_data.get('Company Name', ''),
        company_data.get('Website', ''),
        company_data.get('Contact Email', ''),
        company_data.get('Contact Name', ''),
        company_data.get('Founder/CEO', ''),
        company_data.get('Founder LinkedIn', ''),
        company_data.get('Company LinkedIn', ''),
        company_data.get('Industry', ''),
        company_data.get('Company Size', ''),
        email_subject,
        template_name,
        send_status,
        message_id,
        sent_from,
        campaign_day,
        week_number
    ]

    log_sheet.append_row(log_row)

    # Also log to local file
    log_file = LOG_DIR / "automation.log"
    with open(log_file, 'a') as f:
        log_entry = (
            f"[{log_row[0]}] {send_status} | "
            f"{company_data.get('Company Name', '')} | "
            f"{company_data.get('Contact Email', '')} | "
            f"Sent from: {sent_from} | "
            f"Founder: {company_data.get('Founder/CEO', 'N/A')} | "
            f"LinkedIn: {company_data.get('Founder LinkedIn', 'N/A')} | "
            f"Subject: {email_subject} | "
            f"Template: {template_name} | "
            f"MsgID: {message_id}\n"
        )
        f.write(log_entry)

    return True


def get_send_log(limit=50):
    """Read recent entries from Send Log tab."""
    log_sheet = get_send_log_sheet()
    all_records = log_sheet.get_all_records()
    return all_records[-limit:] if len(all_records) > limit else all_records


# ─── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    """CLI interface for sheet operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage Google Sheet for cold email campaign")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    pending_parser = subparsers.add_parser('pending', help='Get pending companies')
    pending_parser.add_argument('--limit', type=int, help='Max companies to return')

    subparsers.add_parser('count-today', help='Count emails sent today')
    subparsers.add_parser('count-week', help='Count emails sent this week')
    subparsers.add_parser('send-log', help='Show recent send log entries')

    add_parser = subparsers.add_parser('add', help='Add a new company')
    add_parser.add_argument('--name', required=True, help='Company name')
    add_parser.add_argument('--website', required=True, help='Company website')
    add_parser.add_argument('--email', required=True, help='Contact email')
    add_parser.add_argument('--contact', default='', help='Contact name')
    add_parser.add_argument('--industry', default='', help='Industry')

    args = parser.parse_args()

    try:
        if args.command == 'pending':
            companies = get_pending_companies(limit=args.limit)
            print(f"Found {len(companies)} pending companies:")
            for comp in companies:
                print(f"  - {comp.get('Company Name')} ({comp.get('Website')})")

        elif args.command == 'count-today':
            print(f"Emails sent today: {count_sent_today()}")

        elif args.command == 'count-week':
            print(f"Emails sent this week: {count_sent_this_week()}")

        elif args.command == 'send-log':
            entries = get_send_log(limit=20)
            print(f"Last {len(entries)} send log entries:")
            for entry in entries:
                print(f"  [{entry.get('Timestamp')}] {entry.get('Send Status')} - "
                      f"{entry.get('Company Name')} ({entry.get('Contact Email')})")

        elif args.command == 'add':
            if add_company(args.name, args.website, args.email, args.contact, args.industry):
                print(f"Added company: {args.name}")

        else:
            parser.print_help()
        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
