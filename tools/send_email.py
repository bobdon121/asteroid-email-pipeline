#!/usr/bin/env python3
"""
Email Sender - SMTP email delivery for cold email campaigns

Sends HTML + plain text multipart emails via SMTP with retry logic,
email validation, and proper headers for deliverability.
"""

import os
import sys
import re
import time
import uuid
import smtplib
import logging
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate, make_msgid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / ".tmp" / "logs"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logger = logging.getLogger("send_email")
logger.setLevel(logging.DEBUG)

# File handler - detailed logs
file_handler = logging.FileHandler(
    LOG_DIR / "send_email.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(file_handler)

# Console handler - info and above
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(console_handler)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2

# Transient SMTP error codes that are worth retrying
TRANSIENT_ERROR_CODES = {421, 450, 451, 452}


def validate_email(email):
    """
    Basic email format validation.

    Args:
        email: Email address string to validate.

    Returns:
        bool: True if the format looks valid, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def load_smtp_config(account=1):
    """
    Load SMTP credentials and sender info from environment variables.

    Supports dual SMTP accounts (SMTP1_* and SMTP2_*).
    Falls back to legacy SMTP_* variables if numbered vars not found.

    Args:
        account: Which SMTP account to load (1 or 2).

    Returns:
        dict: SMTP and sender configuration.

    Raises:
        ValueError: If any required SMTP variable is missing.
    """
    prefix = f"SMTP{account}"

    required_vars = {
        "SERVER": os.getenv(f"{prefix}_SERVER") or os.getenv("SMTP_SERVER"),
        "PORT": os.getenv(f"{prefix}_PORT") or os.getenv("SMTP_PORT"),
        "EMAIL": os.getenv(f"{prefix}_EMAIL") or os.getenv("SMTP_EMAIL"),
        "PASSWORD": os.getenv(f"{prefix}_PASSWORD") or os.getenv("SMTP_PASSWORD"),
    }

    missing = [f"{prefix}_{k}" for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Check your .env file."
        )

    return {
        "smtp_server": required_vars["SERVER"],
        "smtp_port": int(required_vars["PORT"]),
        "smtp_email": required_vars["EMAIL"],
        "smtp_password": required_vars["PASSWORD"],
        "sender_name": os.getenv("SENDER_NAME", ""),
        "sender_title": os.getenv("SENDER_TITLE", ""),
        "sender_company": os.getenv("SENDER_COMPANY", ""),
        "company_address": os.getenv("COMPANY_ADDRESS", ""),
        "unsubscribe_url": os.getenv("UNSUBSCRIBE_URL", ""),
    }


def build_html_body(plain_text, unsubscribe_url, recipient_email):
    """
    Wrap plain text body in basic HTML with an unsubscribe footer.

    Args:
        plain_text: The plain-text email body.
        unsubscribe_url: Base URL for unsubscribe link.
        recipient_email: Recipient's email for the unsubscribe parameter.

    Returns:
        str: Complete HTML document string.
    """
    # Convert plain text line breaks to HTML
    html_body = plain_text.replace("&", "&amp;")
    html_body = html_body.replace("<", "&lt;").replace(">", "&gt;")
    html_body = html_body.replace("\n", "<br>\n")

    # Build unsubscribe footer
    unsub_footer = ""
    if unsubscribe_url:
        unsub_link = f"{unsubscribe_url}?email={recipient_email}"
        unsub_footer = (
            '<p style="font-size:12px; color:#999; margin-top:30px;">'
            f'<a href="{unsub_link}" style="color:#999;">Unsubscribe</a>'
            "</p>"
        )

    html = f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.6; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
{html_body}
{unsub_footer}
</div>
</body>
</html>"""
    return html


def build_plain_body(body, unsubscribe_url, recipient_email):
    """
    Append an unsubscribe line to the plain-text body.

    Args:
        body: Original plain-text email body.
        unsubscribe_url: Base URL for unsubscribe link.
        recipient_email: Recipient's email for the unsubscribe parameter.

    Returns:
        str: Plain text body with unsubscribe footer.
    """
    if unsubscribe_url:
        unsub_link = f"{unsubscribe_url}?email={recipient_email}"
        return f"{body}\n\n---\nUnsubscribe: {unsub_link}"
    return body


def send_email(recipient_email, subject, body, tracking_id=None, smtp_account=1, cc=None):
    """
    Send an email via SMTP with retry logic.

    Args:
        recipient_email: Recipient's email address.
        subject: Email subject line.
        body: Plain-text email body (will also be wrapped in HTML).
        tracking_id: Optional tracking identifier. Auto-generated if not provided.
        smtp_account: Which SMTP account to use (1 or 2). Defaults to 1.
        cc: Optional CC email address string.

    Returns:
        dict: {
            'success': bool,
            'message_id': str or None,
            'error': str or None
        }
    """
    # Generate tracking ID if not provided
    if not tracking_id:
        tracking_id = uuid.uuid4().hex[:12]

    log_prefix = f"[{tracking_id}][Account {smtp_account}]"

    # Validate recipient email
    if not validate_email(recipient_email):
        error_msg = f"Invalid recipient email format: {recipient_email}"
        logger.error(f"{log_prefix} {error_msg}")
        return {"success": False, "message_id": None, "error": error_msg}

    # Load config for the specified account
    try:
        config = load_smtp_config(account=smtp_account)
        logger.info(f"{log_prefix} Using SMTP: {config['smtp_email']}")
    except ValueError as e:
        logger.error(f"{log_prefix} Configuration error: {e}")
        return {"success": False, "message_id": None, "error": str(e)}

    # Build the MIME message
    msg = MIMEMultipart("alternative")

    # Headers
    msg["From"] = formataddr((config["sender_name"], config["smtp_email"]))
    msg["To"] = recipient_email
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["Reply-To"] = config["smtp_email"]
    msg["Date"] = formatdate(localtime=True)

    # Message-ID for tracking
    domain = config["smtp_email"].split("@")[-1]
    message_id = make_msgid(idstring=tracking_id, domain=domain)
    msg["Message-ID"] = message_id

    # List-Unsubscribe header (improves deliverability)
    if config["unsubscribe_url"]:
        unsub_link = f"{config['unsubscribe_url']}?email={recipient_email}"
        msg["List-Unsubscribe"] = f"<{unsub_link}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    # Attach plain text version (first = fallback)
    plain_text = build_plain_body(
        body, config["unsubscribe_url"], recipient_email
    )
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))

    # Attach HTML version (preferred by most clients)
    html_text = build_html_body(
        body, config["unsubscribe_url"], recipient_email
    )
    msg.attach(MIMEText(html_text, "html", "utf-8"))

    # Send with retry logic
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"{log_prefix} Attempt {attempt}/{MAX_RETRIES} - "
                f"Sending to {recipient_email}"
            )

            with smtplib.SMTP(config["smtp_server"], config["smtp_port"],
                              timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config["smtp_email"], config["smtp_password"])
                all_recipients = [recipient_email] + ([cc] if cc else [])
                server.sendmail(
                    config["smtp_email"],
                    all_recipients,
                    msg.as_string()
                )

            logger.info(
                f"{log_prefix} Email sent successfully to {recipient_email} "
                f"(Message-ID: {message_id})"
            )
            return {
                "success": True,
                "message_id": message_id,
                "error": None,
            }

        except smtplib.SMTPResponseException as e:
            last_error = f"SMTP error {e.smtp_code}: {e.smtp_error}"
            logger.warning(f"{log_prefix} {last_error}")

            if e.smtp_code not in TRANSIENT_ERROR_CODES:
                # Permanent failure, no point retrying
                logger.error(
                    f"{log_prefix} Permanent SMTP error, not retrying."
                )
                return {
                    "success": False,
                    "message_id": message_id,
                    "error": last_error,
                }

        except smtplib.SMTPException as e:
            last_error = f"SMTP exception: {str(e)}"
            logger.warning(f"{log_prefix} {last_error}")

        except OSError as e:
            # Network-level errors (connection refused, timeout, DNS failure)
            last_error = f"Network error: {str(e)}"
            logger.warning(f"{log_prefix} {last_error}")

        # Exponential backoff before next retry
        if attempt < MAX_RETRIES:
            backoff = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
            logger.info(f"{log_prefix} Retrying in {backoff}s...")
            time.sleep(backoff)

    # All retries exhausted
    logger.error(
        f"{log_prefix} All {MAX_RETRIES} attempts failed for "
        f"{recipient_email}. Last error: {last_error}"
    )
    return {
        "success": False,
        "message_id": message_id,
        "error": f"Failed after {MAX_RETRIES} attempts. {last_error}",
    }


def main():
    """CLI interface for testing email delivery."""
    parser = argparse.ArgumentParser(
        description="Send an email via SMTP (WAT framework tool)"
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Recipient email address"
    )
    parser.add_argument(
        "--subject",
        required=True,
        help="Email subject line"
    )
    parser.add_argument(
        "--body",
        required=True,
        help="Plain-text email body"
    )
    parser.add_argument(
        "--tracking-id",
        default=None,
        help="Optional tracking ID (auto-generated if omitted)"
    )
    parser.add_argument(
        "--account",
        type=int,
        default=1,
        choices=[1, 2],
        help="SMTP account to use (1 or 2, default: 1)"
    )

    args = parser.parse_args()

    result = send_email(
        recipient_email=args.to,
        subject=args.subject,
        body=args.body,
        tracking_id=args.tracking_id,
        smtp_account=args.account,
    )

    if result["success"]:
        print(f"SUCCESS: Email sent to {args.to}")
        print(f"  Message-ID: {result['message_id']}")
    else:
        print(f"FAILED: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
