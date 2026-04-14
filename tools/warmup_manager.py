#!/usr/bin/env python3
"""
Warm-up Manager - Enforces email sending limits based on warm-up schedule

For new email domains, this tool ensures we don't send too many emails too fast,
which would trigger spam filters and damage sender reputation.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"


def load_config():
    """Load the automation configuration file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_FILE}\n"
            "Please run setup_automation.py first"
        )

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def calculate_campaign_day(start_date_str):
    """
    Calculate which day of the campaign we're on.

    Args:
        start_date_str: Campaign start date in format "YYYY-MM-DD"

    Returns:
        int: Campaign day number (1, 2, 3, ...)
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    delta = (today - start_date).days

    # Campaign day starts at 1
    return max(1, delta + 1)


def get_current_week(campaign_day):
    """
    Determine which week of the campaign we're in.

    Args:
        campaign_day: Current campaign day number

    Returns:
        int: Week number (1, 2, 3, 4+)
    """
    if campaign_day <= 7:
        return 1
    elif campaign_day <= 14:
        return 2
    elif campaign_day <= 21:
        return 3
    else:
        return 4  # Week 4 and beyond


def get_daily_limit(warmup_schedule, current_week):
    """
    Get the daily sending limit for the current week.

    Args:
        warmup_schedule: List of warmup config dicts with 'week' and 'daily_limit'
        current_week: Current week number

    Returns:
        int: Maximum emails allowed today
    """
    for schedule_item in warmup_schedule:
        if schedule_item['week'] == current_week:
            return schedule_item['daily_limit']

    # If beyond defined schedule, use last defined limit
    return warmup_schedule[-1]['daily_limit']


def get_warmup_status(verbose=False):
    """
    Get current warm-up status and daily limit.

    Returns:
        dict: {
            'warmup_enabled': bool,
            'campaign_day': int,
            'current_week': int,
            'daily_limit': int,
            'campaign_start_date': str
        }
    """
    config = load_config()
    warmup_config = config.get('warmup', {})

    if not warmup_config.get('enabled', False):
        # Warmup disabled, use target volume
        return {
            'warmup_enabled': False,
            'daily_limit': config.get('target_weekly_volume', 50) // 3,  # Divide by 3 days
            'campaign_day': None,
            'current_week': None,
            'campaign_start_date': None
        }

    # Calculate current campaign status
    start_date = warmup_config.get('campaign_start_date')
    if not start_date:
        raise ValueError(
            "Warm-up enabled but no campaign_start_date in config. "
            "Please run setup_automation.py"
        )

    campaign_day = calculate_campaign_day(start_date)
    current_week = get_current_week(campaign_day)
    daily_limit = get_daily_limit(warmup_config.get('schedule', []), current_week)

    status = {
        'warmup_enabled': True,
        'campaign_day': campaign_day,
        'current_week': current_week,
        'daily_limit': daily_limit,
        'campaign_start_date': start_date
    }

    if verbose:
        print(f"Warm-up Status:")
        print(f"  Campaign Day: {campaign_day}")
        print(f"  Current Week: {current_week}")
        print(f"  Daily Limit: {daily_limit} emails")
        print(f"  Start Date: {start_date}")

    return status


def main():
    """CLI interface for checking warm-up status."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check email warm-up status and daily limits"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Show detailed status"
    )

    args = parser.parse_args()

    try:
        status = get_warmup_status(verbose=args.verbose)

        if not args.verbose:
            print(f"Daily Limit: {status['daily_limit']} emails")

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
