#!/usr/bin/env python3
"""
Weekly Research Runner - Sunday batch research orchestrator

Reads up to 10 "Pending" prospects from Google Sheets, runs batch research
using the detailed Prospect Research Intelligence methodology, and updates
the sheet with research results.

Designed to run every Sunday to prepare the next week's outreach batch.

Usage:
    python tools/run_weekly_research.py              # Normal run (up to 10 prospects)
    python tools/run_weekly_research.py --limit 5    # Research only 5
    python tools/run_weekly_research.py --dry-run    # Preview without API calls
    python tools/run_weekly_research.py --force       # Run even if not Sunday
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"
LOG_DIR = PROJECT_ROOT / ".tmp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Add tools directory to path
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "research.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    """Load automation configuration."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def is_research_day(config, force=False):
    """Check if today is a research day (Sunday by default)."""
    if force:
        return True

    import pytz
    timezone_str = config.get('timezone', 'America/New_York')
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    research_day = config.get('research_day', 'Sunday')

    return now.strftime('%A') == research_day


def run_weekly_research(limit=10, dry_run=False, force=False):
    """
    Main weekly research orchestrator.

    Args:
        limit: Max companies to research (default 10, recommended max)
        dry_run: If True, preview what would be researched without API calls
        force: If True, run even if today is not the research day
    """
    logger.info("=" * 60)
    logger.info("WEEKLY RESEARCH - Starting batch research run")
    logger.info("=" * 60)

    # Load config
    config = load_config()
    logger.info(f"Config loaded. Timezone: {config.get('timezone')}")

    # Check if today is research day
    if not is_research_day(config, force=force):
        research_day = config.get('research_day', 'Sunday')
        logger.info(f"Today is not {research_day}. Use --force to override.")
        return {'researched': 0, 'reason': f'Not {research_day}'}

    # Get pending companies from Google Sheet
    from manage_google_sheet import get_pending_companies, update_research_data

    pending = get_pending_companies(limit=limit, status_filter="Pending")

    if not pending:
        logger.info("No pending companies to research. Add prospects to the Google Sheet.")
        return {'researched': 0, 'reason': 'No pending companies'}

    logger.info(f"Found {len(pending)} pending companies (limit: {limit})")

    # Build company list for batch research
    companies = []
    for p in pending:
        company = {
            'company_name': p.get('Company Name', ''),
            'website': p.get('Website', ''),
            'contact_name': p.get('Contact Name', ''),
            'contact_email': p.get('Contact Email', ''),
            'industry': p.get('Industry', ''),
        }
        companies.append(company)
        logger.info(f"  - {company['company_name']} ({company['website']})")

    if dry_run:
        logger.info("[DRY RUN] Would research the following companies:")
        for c in companies:
            logger.info(f"  [DRY RUN] {c['company_name']} - {c['website']}")
        return {'researched': 0, 'reason': 'Dry run', 'would_research': len(companies)}

    # Run batch research
    from research_batch import research_batch

    logger.info(f"\nStarting batch research for {len(companies)} companies...")
    result = research_batch(companies, save_to_file=True)

    # Update Google Sheet with research results
    logger.info("\nUpdating Google Sheet with research results...")
    updated = 0
    failed = 0

    for research_data in result['results']:
        company_name = research_data['company_name']
        try:
            time.sleep(2)  # Rate limit protection for Google Sheets API
            success = update_research_data(company_name, research_data)
            if success:
                updated += 1
                logger.info(f"  [OK] {company_name} (priority: {research_data.get('priority', '?')})")
            else:
                failed += 1
                logger.warning(f"  [FAIL] Could not update {company_name}")
        except Exception as e:
            failed += 1
            logger.error(f"  [ERROR] {company_name}: {str(e)}")

    # Log summary
    logger.info("\n" + "=" * 60)
    logger.info("WEEKLY RESEARCH SUMMARY")
    logger.info(f"  Companies researched: {len(result['results'])}")
    logger.info(f"  Sheet updated: {updated}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total tokens: {result['total_tokens']}")

    if result['priority_matrix']:
        logger.info(f"\nPriority Matrix:\n{result['priority_matrix']}")

    if result['summary']:
        logger.info(f"\nSummary: {result['summary']}")

    logger.info("=" * 60)

    return {
        'researched': len(result['results']),
        'updated': updated,
        'failed': failed,
        'total_tokens': result['total_tokens']
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run weekly batch research on pending prospects"
    )
    parser.add_argument(
        '--limit', '-l',
        type=int, default=10,
        help="Max companies to research (default: 10, recommended max)"
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help="Preview what would be researched without making API calls"
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help="Run even if today is not Sunday"
    )

    args = parser.parse_args()

    try:
        result = run_weekly_research(
            limit=args.limit,
            dry_run=args.dry_run,
            force=args.force
        )

        logger.info(f"Run complete: {result}")
        return 0

    except Exception as e:
        logger.error(f"FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
