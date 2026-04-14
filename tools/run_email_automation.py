#!/usr/bin/env python3
"""
Asteroid.ai Email Automation Pipeline

Reads prospects from Google Sheet, auto-researches each company using the
Asteroid.ai healthcare intelligence methodology (Prompt 1), then generates
personalized cold outreach emails (Prompt 2). Results are written back to
the sheet for manual review and send.

Pipeline per prospect:
  Step 1: Research company (Claude) → write to Column J
  Step 2: Generate email (Claude, only if priority >2 stars) → write to Columns K + L
  Step 3: Update status → "Ready" or "Disqualified"

Nothing is sent automatically. Review the sheet and send manually.

Usage:
  python tools/run_email_automation.py                   # process all pending
  python tools/run_email_automation.py --max-emails 5    # limit to 5
  python tools/run_email_automation.py --dry-run         # preview without Claude calls
  python tools/run_email_automation.py --skip-research   # email-only (use research already in col J)
"""

import sys
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"
LOG_DIR = PROJECT_ROOT / ".tmp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT / "tools"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def run_automation(dry_run=False, max_emails=None, skip_research=False):
    logger.info("=" * 60)
    logger.info("ASTEROID.AI EMAIL PIPELINE - Starting")
    logger.info("=" * 60)

    load_config()

    from manage_google_sheet import get_pending_companies, update_email_content, update_status, update_research_data
    from research_company import research_company, save_research
    from generate_email import generate_email, save_email

    companies = get_pending_companies(status_filter="Pending")
    logger.info(f"Found {len(companies)} pending prospects in Google Sheet")

    if not companies:
        logger.info("No pending prospects. Add rows with Status = 'Pending' to the Google Sheet.")
        return {'researched': 0, 'generated': 0, 'skipped': 0, 'failed': 0}

    if max_emails:
        companies = companies[:max_emails]
        logger.info(f"Limited to {max_emails} this run")

    researched = 0
    generated = 0
    skipped = 0
    failed = 0

    for company in companies:
        company_name = company.get('Company Name', 'Unknown')
        logger.info(f"\n--- {company_name} ---")

        try:
            company_data = {
                'company_name': company_name,
                'website': company.get('Website', ''),
                'contact_email': company.get('Contact Email', ''),
                'contact_name': company.get('Contact Name', ''),
                'contact_title': company.get('Contact Title', ''),
                'description': company.get('Description', ''),
                'industry': company.get('Industry', ''),
                'location': company.get('Location', ''),
            }

            if dry_run:
                logger.info(f"[DRY RUN] Would research and generate email for {company_name}")
                generated += 1
                continue

            # ── Step 1: Research ──────────────────────────────────────────────
            raw_research = company.get('Research Data', '')
            research_data = None

            if skip_research and isinstance(raw_research, str) and raw_research.strip():
                # Use existing research from column J
                try:
                    research_data = json.loads(raw_research)
                    logger.info(f"Using existing research for {company_name}")
                except json.JSONDecodeError:
                    research_data = {'research_text': raw_research, 'priority': '3'}
            elif skip_research:
                logger.info(f"No research in sheet for {company_name}, running research anyway")

            if research_data is None:
                logger.info(f"Researching {company_name}...")
                research_data = research_company(
                    company_name,
                    company_data['website'],
                    contact_name=company_data['contact_name'],
                    contact_title=company_data['contact_title'],
                    industry=company_data['industry'],
                    description=company_data['description'],
                    location=company_data['location'],
                )
                save_research(research_data, company_name)
                update_research_data(company_name, research_data)
                researched += 1
                logger.info(f"Research done — Priority: {research_data.get('priority')} stars | Use case: {research_data.get('primary_use_case')}")

                # Brief pause between API calls
                time.sleep(3)

            # ── Step 2: Generate Email ────────────────────────────────────────
            logger.info(f"Generating email for {company_name}...")
            email_data = generate_email(company_data, research_data)

            if not email_data.get('qualified'):
                priority = email_data.get('priority', '?')
                logger.info(f"DISQUALIFIED: {company_name} — Priority {priority} stars (needs >2) or no ICP match")
                update_status(company_name, "Disqualified")
                skipped += 1
                continue

            # ── Step 3: Write to Sheet ────────────────────────────────────────
            save_email(email_data, company_name)
            update_email_content(
                company_name,
                email_data['subject'],
                email_data['body'],
                'asteroid-outreach-v1'
            )

            logger.info(f"DONE: {company_name} | Subject: {email_data['subject']}")
            generated += 1

            time.sleep(2)

        except Exception as e:
            logger.error(f"ERROR — {company_name}: {e}")
            failed += 1
            continue

    logger.info("\n" + "=" * 60)
    logger.info(f"Researched: {researched} | Emails generated: {generated} | Disqualified: {skipped} | Failed: {failed}")
    logger.info("Review Google Sheet — 'Ready' rows have emails in cols K & L")
    logger.info("=" * 60)

    return {'researched': researched, 'generated': generated, 'skipped': skipped, 'failed': failed}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Asteroid.ai email pipeline: research + generate → Google Sheet")
    parser.add_argument('--dry-run', '-d', action='store_true', help="Preview without Claude calls")
    parser.add_argument('--max-emails', '-m', type=int, help="Limit prospects processed this run")
    parser.add_argument('--skip-research', action='store_true', help="Skip research step, use existing col J data")
    args = parser.parse_args()

    try:
        result = run_automation(
            dry_run=args.dry_run,
            max_emails=args.max_emails,
            skip_research=args.skip_research,
        )
        return 0 if result['failed'] == 0 else 1
    except Exception as e:
        logger.error(f"FATAL: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
