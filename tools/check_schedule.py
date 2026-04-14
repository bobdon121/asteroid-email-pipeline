#!/usr/bin/env python3
"""
Schedule Checker - Timezone-aware scheduling for cold email campaign

Checks if current time is within the allowed sending window:
- Only Tue/Wed/Thu
- Only 9 AM - 11 AM in target timezone
- Respects warm-up limits
"""

import os
import sys
import json
from datetime import datetime, time
from pathlib import Path
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"

# Import warmup manager
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from warmup_manager import get_warmup_status


def load_config():
    """Load the automation configuration file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_FILE}\n"
            "Please run setup_automation.py first"
        )

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def get_current_time_in_timezone(timezone_str):
    """
    Get current time in the specified timezone.

    Args:
        timezone_str: Timezone string (e.g., "America/New_York", "Europe/London")

    Returns:
        datetime: Current time in specified timezone
    """
    try:
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {timezone_str}. Error: {e}")


def is_allowed_day(current_time, allowed_days):
    """
    Check if current day is in the allowed sending days.

    Args:
        current_time: datetime object in target timezone
        allowed_days: List of allowed day names (e.g., ["Tuesday", "Wednesday", "Thursday"])

    Returns:
        bool: True if today is an allowed day
    """
    current_day_name = current_time.strftime("%A")
    return current_day_name in allowed_days


def is_within_time_window(current_time, start_time_str, end_time_str):
    """
    Check if current time is within the allowed sending window.

    Args:
        current_time: datetime object in target timezone
        start_time_str: Start time string (e.g., "09:00")
        end_time_str: End time string (e.g., "11:00")

    Returns:
        bool: True if current time is within window
    """
    current_time_only = current_time.time()

    start_time = time(*map(int, start_time_str.split(':')))
    end_time = time(*map(int, end_time_str.split(':')))

    return start_time <= current_time_only <= end_time


def count_emails_sent_today(config):
    """
    Count how many emails were sent today (reads from Google Sheet or log).

    For now, this is a placeholder that returns 0.
    Will be implemented when we integrate with manage_google_sheet.py

    Returns:
        int: Number of emails sent today
    """
    # TODO: Integrate with Google Sheets to get actual count
    # For now, return 0 as placeholder
    return 0


def check_can_send(verbose=False, test_mode=False):
    """
    Check if emails can be sent right now.

    Args:
        verbose: Print detailed status info
        test_mode: Override schedule checks (for testing)

    Returns:
        dict: {
            'can_send': bool,
            'reason': str,
            'max_emails_today': int,
            'sent_today': int,
            'remaining_today': int,
            'current_time': str,
            'current_day': str
        }
    """
    config = load_config()

    # Get current time in target timezone
    timezone_str = config.get('timezone', 'America/New_York')
    current_time = get_current_time_in_timezone(timezone_str)
    current_day_name = current_time.strftime("%A")

    # Get warm-up status
    warmup_status = get_warmup_status()
    max_emails_today = warmup_status['daily_limit']

    # Count emails sent today
    sent_today = count_emails_sent_today(config)
    remaining_today = max(0, max_emails_today - sent_today)

    result = {
        'can_send': False,
        'reason': '',
        'max_emails_today': max_emails_today,
        'sent_today': sent_today,
        'remaining_today': remaining_today,
        'current_time': current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        'current_day': current_day_name,
        'timezone': timezone_str
    }

    # Test mode bypasses all checks
    if test_mode:
        if remaining_today > 0:
            result['can_send'] = True
            result['reason'] = "Test mode - schedule checks bypassed"
        else:
            result['reason'] = "Daily limit reached"
        return result

    # Check if today is an allowed day
    allowed_days = config.get('send_days', ['Tuesday', 'Wednesday', 'Thursday'])
    if not is_allowed_day(current_time, allowed_days):
        result['reason'] = f"Not an allowed sending day (allowed: {', '.join(allowed_days)})"
        if verbose:
            print(f"[X] {result['reason']}")
        return result

    # Check if within time window
    start_time = config.get('send_time_start', '09:00')
    end_time = config.get('send_time_end', '11:00')
    if not is_within_time_window(current_time, start_time, end_time):
        result['reason'] = f"Outside sending window ({start_time} - {end_time} {timezone_str})"
        if verbose:
            print(f"[X] {result['reason']}")
        return result

    # Check if daily limit reached
    if remaining_today <= 0:
        result['reason'] = f"Daily limit reached ({max_emails_today} emails)"
        if verbose:
            print(f"[X] {result['reason']}")
        return result

    # All checks passed!
    result['can_send'] = True
    result['reason'] = "All checks passed - ready to send"

    if verbose:
        print(f"[OK] Can send emails!")
        print(f"   Current time: {result['current_time']}")
        print(f"   Remaining today: {remaining_today}/{max_emails_today}")
        if warmup_status['warmup_enabled']:
            print(f"   Warm-up: Week {warmup_status['current_week']}, Day {warmup_status['campaign_day']}")

    return result


def main():
    """CLI interface for checking schedule."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check if emails can be sent right now"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Show detailed status"
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help="Test mode - bypass day/time checks"
    )

    args = parser.parse_args()

    try:
        result = check_can_send(verbose=args.verbose, test_mode=args.test)

        if not args.verbose:
            if result['can_send']:
                print(f"[OK] Can send {result['remaining_today']} emails")
            else:
                print(f"[X] Cannot send: {result['reason']}")

        return 0 if result['can_send'] else 1

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
