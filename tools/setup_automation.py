#!/usr/bin/env python3
"""
Setup Wizard - Interactive setup for cold email campaign automation

Walks through:
1. Timezone selection
2. Target volume configuration
3. Service description
4. SMTP credentials and test
5. API key validation (Anthropic)
6. Google Sheets OAuth setup
7. Create tracking spreadsheet
8. Generate config file
9. Show next steps
"""

import os
import sys
import json
import smtplib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv, set_key

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "email_automation_config.json"
ENV_FILE = PROJECT_ROOT / ".env"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def print_header(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_step(step_num, total, description):
    """Print step progress."""
    print(f"\n[Step {step_num}/{total}] {description}")
    print("-" * 40)


def get_input(prompt, default=None, required=True):
    """Get user input with optional default."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        while True:
            user_input = input(f"{prompt}: ").strip()
            if user_input or not required:
                return user_input
            print("This field is required. Please enter a value.")


def setup_timezone():
    """Configure timezone."""
    print("Common timezones:")
    timezones = {
        "1": ("America/New_York", "US Eastern (New York)"),
        "2": ("America/Chicago", "US Central (Chicago)"),
        "3": ("America/Denver", "US Mountain (Denver)"),
        "4": ("America/Los_Angeles", "US Pacific (Los Angeles)"),
        "5": ("Europe/London", "UK (London)"),
        "6": ("Europe/Berlin", "Central Europe (Berlin)"),
        "7": ("Asia/Kolkata", "India (Kolkata)"),
        "8": ("Asia/Singapore", "Singapore"),
        "9": ("Asia/Dubai", "UAE (Dubai)"),
        "10": ("Australia/Sydney", "Australia (Sydney)"),
    }

    for key, (tz, label) in timezones.items():
        print(f"  {key}. {label} ({tz})")
    print(f"  0. Enter custom timezone")

    choice = get_input("\nSelect timezone number", default="1")

    if choice == "0":
        return get_input("Enter timezone (e.g., America/New_York)")
    elif choice in timezones:
        return timezones[choice][0]
    else:
        print("Invalid choice. Using America/New_York")
        return "America/New_York"


def setup_volume():
    """Configure email volume."""
    print("Recommended: Start with 50 emails/week (warm-up will handle daily limits)")
    weekly = get_input("Target weekly email volume", default="50")
    try:
        weekly = int(weekly)
    except ValueError:
        weekly = 50
    return weekly


def setup_service_info():
    """Collect service information for AI context."""
    name = get_input("What is your service/company name?")
    description = get_input("Briefly describe your service (1-2 sentences)")
    target = get_input("Who is your target audience? (industry, role, company size)")

    return {
        "name": name,
        "description": description,
        "target_audience": target
    }


def setup_smtp():
    """Configure and test dual SMTP credentials (2 Gmail accounts)."""
    print("This system uses 2 Gmail accounts that alternate sending emails")
    print("(round-robin) to protect against spam flags.\n")
    print("For EACH account, you need:")
    print("  1. Enable 2-Step Verification in your Google Account")
    print("  2. Go to: Google Account > Security > App Passwords")
    print("  3. Generate a password for 'Mail'\n")

    all_ok = True

    for acct_num in [1, 2]:
        print(f"\n--- SMTP Account {acct_num} ---")
        email = get_input(f"Gmail address (Account {acct_num})")
        password = get_input(f"App-specific password (Account {acct_num})")
        server = get_input(f"SMTP server (Account {acct_num})", default="smtp.gmail.com")
        port = get_input(f"SMTP port (Account {acct_num})", default="587")

        # Save to .env with numbered prefix
        set_key(str(ENV_FILE), f"SMTP{acct_num}_SERVER", server)
        set_key(str(ENV_FILE), f"SMTP{acct_num}_PORT", port)
        set_key(str(ENV_FILE), f"SMTP{acct_num}_EMAIL", email)
        set_key(str(ENV_FILE), f"SMTP{acct_num}_PASSWORD", password)

        # Use Account 1 as the IMAP inbox for reply checking
        if acct_num == 1:
            set_key(str(ENV_FILE), "IMAP_SERVER", "imap.gmail.com")
            set_key(str(ENV_FILE), "IMAP_PORT", "993")
            set_key(str(ENV_FILE), "IMAP_EMAIL", email)
            set_key(str(ENV_FILE), "IMAP_PASSWORD", password)

        # Test connection
        print(f"\nTesting SMTP Account {acct_num} ({email})...")
        try:
            with smtplib.SMTP(server, int(port)) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(email, password)
            print(f"Account {acct_num} SMTP connection successful!")
        except Exception as e:
            print(f"Account {acct_num} SMTP test FAILED: {str(e)}")
            print("You can fix this later in the .env file.")
            all_ok = False

    return all_ok


def setup_sender_info():
    """Collect sender information."""
    name = get_input("Your full name (appears as email sender)")
    title = get_input("Your job title")
    company = get_input("Your company name")
    phone = get_input("Phone number (optional)", required=False)
    address = get_input("Business address (required for CAN-SPAM compliance)")

    set_key(str(ENV_FILE), "SENDER_NAME", name)
    set_key(str(ENV_FILE), "SENDER_TITLE", title)
    set_key(str(ENV_FILE), "SENDER_COMPANY", company)
    if phone:
        set_key(str(ENV_FILE), "SENDER_PHONE", phone)
    set_key(str(ENV_FILE), "COMPANY_ADDRESS", address)

    return {
        "name": name,
        "title": title,
        "company": company,
        "phone": phone,
        "address": address
    }



def test_anthropic_key():
    """Test Anthropic API key."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_anthropic_api_key_here':
        api_key = get_input("Enter your Anthropic API key")
        set_key(str(ENV_FILE), "ANTHROPIC_API_KEY", api_key)

    print("Testing Anthropic API key...")
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'API key works' in 3 words"}]
        )
        print(f"Anthropic API: {response.content[0].text}")
        return True
    except Exception as e:
        print(f"Anthropic test FAILED: {str(e)}")
        print("You can update the key later in .env")
        return False


def setup_google_sheets():
    """Set up Google Sheets and create tracking spreadsheet."""
    print("To use Google Sheets API, you need:")
    print("  1. Go to https://console.cloud.google.com/")
    print("  2. Create a new project (or select existing)")
    print("  3. Enable 'Google Sheets API' and 'Google Drive API'")
    print("  4. Create OAuth 2.0 credentials (Desktop application)")
    print("  5. Download credentials.json to project root\n")

    creds_file = PROJECT_ROOT / "credentials.json"
    if not creds_file.exists():
        print(f"credentials.json not found at: {creds_file}")
        input("Place credentials.json in the project root, then press Enter...")

    if creds_file.exists():
        print("\nCreating Google Sheet...")
        try:
            from setup_google_sheet import create_tracking_sheet
            result = create_tracking_sheet()
            set_key(str(ENV_FILE), "GOOGLE_SHEET_ID", result['sheet_id'])
            return result['sheet_id']
        except Exception as e:
            print(f"Google Sheets setup FAILED: {str(e)}")
            print("You can set this up later by running: python tools/setup_google_sheet.py")
            return None
    else:
        print("Skipping Google Sheets setup. Run later: python tools/setup_google_sheet.py")
        return None


def generate_config(timezone, weekly_volume, service_info, sheet_id=None):
    """Generate the automation config file."""
    config = {
        "timezone": timezone,
        "send_days": ["Tuesday", "Wednesday", "Thursday"],
        "send_time_start": "09:00",
        "send_time_end": "11:00",

        "warmup": {
            "enabled": True,
            "campaign_start_date": datetime.now().strftime("%Y-%m-%d"),
            "schedule": [
                {"week": 1, "daily_limit": 10},
                {"week": 2, "daily_limit": 20},
                {"week": 3, "daily_limit": 35},
                {"week": 4, "daily_limit": weekly_volume // 3}
            ]
        },

        "target_weekly_volume": weekly_volume,
        "emails_per_send_window": weekly_volume // 3,
        "delay_between_emails": 45,

        "google_sheet_id": sheet_id or "",
        "tracking_domain": "",
        "unsubscribe_url": "",

        "service_info": service_info,

        "templates": {
            "directory": "templates/",
            "rotation": "round-robin"
        }
    }

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nConfig saved to: {CONFIG_FILE}")
    return config


def show_next_steps(config):
    """Display next steps after setup."""
    print_header("SETUP COMPLETE! Next Steps:")

    print("""
1. ADD EMAIL TEMPLATES
   Place your email templates in the templates/ directory:
   - templates/template1.md
   - templates/template2.md
   See templates/template_guide.md for format instructions.

2. ADD PROSPECT DATA
   Add companies to your Google Sheet (Prospects tab):
   - Company Name, Website, Contact Email, Contact Name, Industry

3. TEST RUN (recommended)
   python tools/run_email_automation.py --test-mode --dry-run --max-emails 3
   This will research + generate emails without sending.

4. FIRST REAL SEND
   python tools/run_email_automation.py --test-mode --max-emails 1
   Send to one company first to verify everything works.

5. SET UP SCHEDULING (Windows Task Scheduler)
   Create two scheduled tasks:

   Task 1 - Email Sender (every 30 min):
     Program: python
     Arguments: "tools/run_email_automation.py"
     Start in: "{PROJECT_ROOT}"

   Task 2 - Reply Checker (every 30 min):
     Program: python
     Arguments: "tools/check_replies.py"
     Start in: "{PROJECT_ROOT}"

6. MONITOR
   - Check .tmp/logs/automation.log for activity
   - Review Google Sheet 'Send Log' tab for detailed records
   - Review 'Campaign Stats' tab for performance

WARM-UP SCHEDULE (automatic):
  Week 1: 10 emails/day (30/week)
  Week 2: 20 emails/day (60/week)
  Week 3: 35 emails/day (105/week)
  Week 4+: {config.get('emails_per_send_window', 17)} emails/day ({config.get('target_weekly_volume', 50)}/week)
""")


def main():
    """Run the interactive setup wizard."""
    print_header("COLD EMAIL CAMPAIGN - Setup Wizard")

    total_steps = 7

    # Step 1: Timezone
    print_step(1, total_steps, "Timezone Configuration")
    timezone = setup_timezone()
    print(f"\nTimezone set to: {timezone}")

    # Step 2: Volume
    print_step(2, total_steps, "Email Volume")
    weekly_volume = setup_volume()
    print(f"\nTarget: {weekly_volume} emails/week")

    # Step 3: Service info
    print_step(3, total_steps, "Service Information")
    service_info = setup_service_info()

    # Step 4: Sender info
    print_step(4, total_steps, "Sender Information")
    sender_info = setup_sender_info()

    # Step 5: SMTP
    print_step(5, total_steps, "Email (SMTP) Configuration")
    smtp_ok = setup_smtp()

    # Step 6: API Keys
    print_step(6, total_steps, "API Key Validation")
    print("\n--- Anthropic (Claude) ---")
    anthropic_ok = test_anthropic_key()

    # Step 7: Google Sheets
    print_step(7, total_steps, "Google Sheets Setup")
    sheet_id = setup_google_sheets()

    # Generate config
    print_header("Generating Configuration")
    config = generate_config(timezone, weekly_volume, service_info, sheet_id)

    # Summary
    print_header("Setup Summary")
    print(f"  Timezone:       {timezone}")
    print(f"  Weekly Volume:  {weekly_volume}")
    print(f"  Service:        {service_info['name']}")
    print(f"  Sender:         {sender_info['name']} ({sender_info['company']})")
    print(f"  SMTP (2 accts): {'OK' if smtp_ok else 'NEEDS FIX'}")
    print(f"  Anthropic:      {'OK' if anthropic_ok else 'NEEDS FIX'}")
    print(f"  Google Sheets:  {'OK' if sheet_id else 'NEEDS SETUP'}")
    print(f"  Config:         {CONFIG_FILE}")

    # Next steps
    show_next_steps(config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
