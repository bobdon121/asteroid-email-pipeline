#!/usr/bin/env python3
"""
Airtable Prospect Extractor - Pulls prospect data from Airtable into Google Sheet

Extracts companies from an Airtable base, filters by target contact titles
(CMO, CTO, CEO), and loads them into the Prospects tab of the Google Sheet.

Required:
  - AIRTABLE_API_TOKEN in .env (Personal Access Token with data.records:read scope)
  - AIRTABLE_BASE_ID in .env (from your Airtable URL: airtable.com/appXXXXXXX/...)
  - AIRTABLE_TABLE_NAME in .env (table name, default: "Companies" or the table name)

Usage:
    python tools/extract_airtable.py --preview              # Preview data without loading
    python tools/extract_airtable.py --load-sheet            # Extract and load into Google Sheet
    python tools/extract_airtable.py --load-sheet --limit 50 # Load 50 prospects
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Add tools directory to path
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

# Target contact titles for design/dev outreach
TARGET_TITLES = [
    "cmo", "chief marketing officer",
    "cto", "chief technology officer",
    "ceo", "chief executive officer",
    "founder", "co-founder", "cofounder",
    "vp of marketing", "vp marketing",
    "vp of product", "vp product",
    "head of marketing", "head of design",
    "head of product", "head of digital",
    "director of marketing", "director of product",
    "creative director",
]

# Titles to exclude
EXCLUDE_TITLES = [
    "clo", "chief legal officer",
    "cfo", "chief financial officer",
    "general counsel", "legal",
    "accountant", "controller",
]


def parse_airtable_url(url):
    """
    Extract base_id and table_id from an Airtable URL.

    URLs look like: https://airtable.com/appXXXXXXX/tblXXXXXXX/viwXXXXXXX
    or: https://airtable.com/appXXXXXXX/shrXXXXXXX (shared views)

    Returns:
        tuple: (base_id, table_id_or_none)
    """
    # Match app ID
    app_match = re.search(r'(app[a-zA-Z0-9]+)', url)
    base_id = app_match.group(1) if app_match else None

    # Match table ID
    tbl_match = re.search(r'(tbl[a-zA-Z0-9]+)', url)
    table_id = tbl_match.group(1) if tbl_match else None

    return base_id, table_id


def is_target_title(title):
    """Check if a contact title matches our target titles."""
    if not title:
        return False
    title_lower = title.lower().strip()

    # Check exclusions first
    for exclude in EXCLUDE_TITLES:
        if exclude in title_lower:
            return False

    # Check target titles
    for target in TARGET_TITLES:
        if target in title_lower:
            return True

    return False


def get_field_value(record_fields, possible_names, default=""):
    """
    Get a field value trying multiple possible column names.

    Airtable columns can have varied names, so we try common variations.
    """
    for name in possible_names:
        if name in record_fields:
            val = record_fields[name]
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val else default
    return default


def extract_from_airtable(base_id=None, table_name=None, api_token=None,
                          limit=50, filter_titles=True):
    """
    Extract prospect data from Airtable.

    Args:
        base_id: Airtable base ID (appXXXXXX). Falls back to AIRTABLE_BASE_ID env var.
        table_name: Table name or ID. Falls back to AIRTABLE_TABLE_NAME env var.
        api_token: Personal Access Token. Falls back to AIRTABLE_API_TOKEN env var.
        limit: Max records to extract (default 50)
        filter_titles: Whether to filter by target contact titles

    Returns:
        list: List of prospect dicts with standardized field names
    """
    from pyairtable import Api

    # Resolve credentials
    api_token = api_token or os.getenv('AIRTABLE_API_TOKEN')
    base_id = base_id or os.getenv('AIRTABLE_BASE_ID')
    table_name = table_name or os.getenv('AIRTABLE_TABLE_NAME', 'Companies')

    if not api_token:
        raise ValueError(
            "AIRTABLE_API_TOKEN not found. "
            "Create one at https://airtable.com/create/tokens with data.records:read scope, "
            "then add it to .env"
        )
    if not base_id:
        raise ValueError(
            "AIRTABLE_BASE_ID not found. "
            "Get it from your Airtable URL (the appXXXXXX part), then add to .env"
        )

    print(f"Connecting to Airtable (base: {base_id}, table: {table_name})...")

    api = Api(api_token)
    table = api.table(base_id, table_name)

    # Fetch all records
    print("Fetching records...")
    all_records = table.all()
    print(f"Fetched {len(all_records)} total records from Airtable")

    # Map Airtable fields to our standard format
    # Common Airtable column name variations
    FIELD_MAP = {
        'company_name': ['Name', 'Company Name', 'Company', 'Organization', 'Organization Name', 'company_name'],
        'website': ['Website', 'URL', 'Domain', 'Company Website', 'website', 'Web'],
        'industry': ['Industry', 'Sector', 'Category', 'industry', 'Field'],
        'description': ['Description', 'About', 'Bio', 'Notes', 'Company Description', 'description'],
        'linkedin': ['LinkedIn URL', 'LinkedIn', 'Company LinkedIn', 'linkedin', 'LinkedIn Profile'],
        'country': ['Country', 'Location', 'HQ Country', 'country', 'Region'],
        'address': ['Address', 'HQ Address', 'City', 'Location', 'address'],
        'contact_name': ['Contact Name', 'Contact', 'First Name', 'Full Name', 'contact_name', 'Person', 'Contact Person'],
        'contact_title': ['Contact Title', 'Title', 'Job Title', 'Role', 'Position', 'contact_title'],
        'contact_email': ['Contact Email', 'Email', 'email', 'Work Email', 'contact_email', 'Email Address'],
    }

    prospects = []

    for record in all_records:
        fields = record.get('fields', {})

        # Map fields
        prospect = {}
        for our_field, possible_names in FIELD_MAP.items():
            prospect[our_field] = get_field_value(fields, possible_names)

        # Skip if no company name or website
        if not prospect['company_name']:
            continue

        # Filter by contact title if enabled
        if filter_titles and prospect['contact_title']:
            if not is_target_title(prospect['contact_title']):
                continue
        elif filter_titles and not prospect['contact_title']:
            # No title info — include but flag for review
            prospect['_needs_title_review'] = True

        prospects.append(prospect)

        if len(prospects) >= limit:
            break

    print(f"Extracted {len(prospects)} prospects (filtered by title: {filter_titles})")
    return prospects


def load_to_google_sheet(prospects):
    """
    Load prospects into the Google Sheet Prospects tab.

    Args:
        prospects: List of prospect dicts

    Returns:
        int: Number of prospects loaded
    """
    from manage_google_sheet import add_company

    loaded = 0
    for i, p in enumerate(prospects):
        try:
            add_company(
                company_name=p['company_name'],
                website=p['website'],
                contact_email=p['contact_email'],
                contact_name=p['contact_name'],
                industry=p['industry']
            )
            loaded += 1
            print(f"  [{loaded}] Added: {p['company_name']} ({p['contact_title']})")

            # Rate limit protection
            if (i + 1) % 10 == 0:
                print(f"    ... pausing to avoid rate limits ...")
                time.sleep(3)
            else:
                time.sleep(1)

        except Exception as e:
            print(f"  [ERROR] Failed to add {p['company_name']}: {str(e)}")

    return loaded


def save_to_csv(prospects, filename="prospects_export.csv"):
    """Save prospects to CSV for review."""
    import csv

    filepath = TMP_DIR / filename

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'company_name', 'website', 'industry', 'description',
            'linkedin', 'country', 'address',
            'contact_name', 'contact_title', 'contact_email'
        ])
        writer.writeheader()
        for p in prospects:
            row = {k: v for k, v in p.items() if not k.startswith('_')}
            writer.writerow(row)

    print(f"Saved {len(prospects)} prospects to: {filepath}")
    return filepath


def extract_from_csv(csv_path, limit=50, filter_titles=True):
    """
    Extract prospect data from a CSV file (exported from Airtable).

    Args:
        csv_path: Path to CSV file
        limit: Max records to extract
        filter_titles: Whether to filter by target contact titles

    Returns:
        list: List of prospect dicts with standardized field names
    """
    import csv

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print(f"Reading CSV: {csv_path}")

    # Common Airtable column name variations (same as API version)
    FIELD_MAP = {
        'company_name': ['Name', 'Company Name', 'Company', 'Organization', 'Organization Name', 'company_name'],
        'website': ['Website', 'URL', 'Domain', 'Company Website', 'website', 'Web'],
        'industry': ['Industry', 'Sector', 'Category', 'industry', 'Field'],
        'description': ['Description', 'About', 'Bio', 'Notes', 'Company Description', 'description'],
        'linkedin': ['LinkedIn URL', 'LinkedIn', 'Company LinkedIn', 'linkedin', 'LinkedIn Profile'],
        'country': ['Country', 'Location', 'HQ Country', 'country', 'Region'],
        'address': ['Address', 'HQ Address', 'City', 'Location', 'address'],
        'contact_name': ['Contact Name', 'Contact', 'First Name', 'Full Name', 'contact_name', 'Person', 'Contact Person'],
        'contact_title': ['Contact Title', 'Title', 'Job Title', 'Role', 'Position', 'contact_title'],
        'contact_email': ['Contact Email', 'Email', 'email', 'Work Email', 'contact_email', 'Email Address'],
    }

    prospects = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_columns = reader.fieldnames
        print(f"CSV columns found: {csv_columns}")

        # Build column mapping: our_field -> actual CSV column name
        col_map = {}
        for our_field, possible_names in FIELD_MAP.items():
            for name in possible_names:
                if name in csv_columns:
                    col_map[our_field] = name
                    break

        print(f"Column mapping: {col_map}")

        unmapped = [c for c in csv_columns if c not in col_map.values()]
        if unmapped:
            print(f"Unmapped columns (ignored): {unmapped}")

        for row in reader:
            prospect = {}
            for our_field, csv_col in col_map.items():
                prospect[our_field] = str(row.get(csv_col, '')).strip()

            # Fill any missing fields with empty string
            for field in FIELD_MAP:
                if field not in prospect:
                    prospect[field] = ''

            # Skip if no company name
            if not prospect['company_name']:
                continue

            # Filter by contact title if enabled
            if filter_titles and prospect['contact_title']:
                if not is_target_title(prospect['contact_title']):
                    continue
            elif filter_titles and not prospect['contact_title']:
                prospect['_needs_title_review'] = True

            prospects.append(prospect)

            if len(prospects) >= limit:
                break

    print(f"Extracted {len(prospects)} prospects from CSV (filtered by title: {filter_titles})")
    return prospects


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract prospects from Airtable (API or CSV) and load into Google Sheet"
    )
    parser.add_argument(
        '--csv',
        help="Path to CSV file exported from Airtable (no API token needed)"
    )
    parser.add_argument(
        '--url',
        help="Airtable URL (extracts base_id automatically, requires API token)"
    )
    parser.add_argument(
        '--base-id',
        help="Airtable base ID (appXXXXXXX)"
    )
    parser.add_argument(
        '--table',
        help="Table name or ID (default: from .env or 'Companies')"
    )
    parser.add_argument(
        '--limit', type=int, default=50,
        help="Max prospects to extract (default: 50)"
    )
    parser.add_argument(
        '--no-filter',
        action='store_true',
        help="Skip title filtering (extract all contacts)"
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help="Preview extracted data without loading to sheet"
    )
    parser.add_argument(
        '--load-sheet',
        action='store_true',
        help="Load extracted prospects into Google Sheet"
    )
    parser.add_argument(
        '--save-csv',
        action='store_true',
        help="Save extracted data to CSV"
    )

    args = parser.parse_args()

    try:
        prospects = []

        if args.csv:
            # CSV mode — no API token needed
            prospects = extract_from_csv(
                args.csv,
                limit=args.limit,
                filter_titles=not args.no_filter
            )
        else:
            # API mode — requires token
            base_id = args.base_id
            table_name = args.table

            if args.url:
                parsed_base, parsed_table = parse_airtable_url(args.url)
                if parsed_base:
                    base_id = parsed_base
                    print(f"Parsed base ID from URL: {base_id}")
                if parsed_table and not table_name:
                    table_name = parsed_table
                    print(f"Parsed table ID from URL: {table_name}")

            prospects = extract_from_airtable(
                base_id=base_id,
                table_name=table_name,
                limit=args.limit,
                filter_titles=not args.no_filter
            )

        if not prospects:
            print("No prospects extracted. Check your Airtable credentials and field names.")
            return 1

        # Preview
        print(f"\n{'='*80}")
        print(f"EXTRACTED {len(prospects)} PROSPECTS")
        print(f"{'='*80}")
        for i, p in enumerate(prospects, 1):
            flag = " [NEEDS TITLE REVIEW]" if p.get('_needs_title_review') else ""
            print(f"  {i}. {p['company_name']}")
            print(f"     Web: {p['website']} | Industry: {p['industry']}")
            print(f"     Contact: {p['contact_name']} ({p['contact_title']}){flag}")
            print(f"     Email: {p['contact_email']}")
            print()

        # Save to CSV
        if args.save_csv or args.preview:
            save_to_csv(prospects)

        # Load to Google Sheet
        if args.load_sheet:
            print(f"\nLoading {len(prospects)} prospects into Google Sheet...")
            loaded = load_to_google_sheet(prospects)
            print(f"\nDone. Loaded {loaded}/{len(prospects)} prospects into Google Sheet.")
        elif not args.preview:
            print("\nUse --load-sheet to load these into the Google Sheet")
            print("Use --preview to save a CSV for review first")

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
