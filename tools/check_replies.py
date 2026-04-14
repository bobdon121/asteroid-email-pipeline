#!/usr/bin/env python3
"""
IMAP Reply Checker - Detects replies to cold email campaign messages

Connects to an IMAP inbox and searches for replies to emails sent as part of
the cold email campaign. When a reply is found, it matches the sender back to
a contact in the Google Sheet and marks them as replied.

Matching strategy (in order of reliability):
  1. In-Reply-To / References headers matching a known Message-ID
  2. Subject line prefix "Re:" combined with sender email matching a contact

Required .env variables:
  IMAP_SERVER   - IMAP server hostname (e.g. imap.gmail.com)
  IMAP_PORT     - IMAP server port (default 993)
  IMAP_EMAIL    - Email address to authenticate with
  IMAP_PASSWORD - Email account password or app-specific password
"""

import os
import sys
import logging
import argparse
import email
import email.policy
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
LOG_DIR = PROJECT_ROOT / ".tmp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Make sibling tools importable
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

# ─── LOGGING ────────────────────────────────────────────────────────────────────

logger = logging.getLogger("check_replies")
logger.setLevel(logging.DEBUG)

# File handler - always logs to disk
_file_handler = logging.FileHandler(LOG_DIR / "replies.log", encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
logger.addHandler(_file_handler)

# Console handler - added later if --verbose is used
_console_handler = None


def _enable_console_logging():
    """Attach a console handler so log messages are also printed to stdout."""
    global _console_handler
    if _console_handler is None:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setLevel(logging.DEBUG)
        _console_handler.setFormatter(
            logging.Formatter("%(levelname)s  %(message)s")
        )
        logger.addHandler(_console_handler)


# ─── IMAP HELPERS ────────────────────────────────────────────────────────────────

def _get_imap_credentials():
    """Read IMAP credentials from environment, raising on missing values."""
    server = os.getenv("IMAP_SERVER")
    port = os.getenv("IMAP_PORT", "993")
    email_addr = os.getenv("IMAP_EMAIL")
    password = os.getenv("IMAP_PASSWORD")

    missing = []
    if not server:
        missing.append("IMAP_SERVER")
    if not email_addr:
        missing.append("IMAP_EMAIL")
    if not password:
        missing.append("IMAP_PASSWORD")

    if missing:
        raise EnvironmentError(
            f"Missing required .env variables: {', '.join(missing)}. "
            "Please add them to your .env file."
        )

    return server, int(port), email_addr, password


def _connect_imap():
    """
    Create and return an authenticated IMAPClient connection.

    Returns:
        imapclient.IMAPClient: Logged-in IMAP connection.
    """
    import imapclient

    server, port, email_addr, password = _get_imap_credentials()

    logger.info("Connecting to IMAP server %s:%d as %s", server, port, email_addr)
    client = imapclient.IMAPClient(server, port=port, ssl=True)

    try:
        client.login(email_addr, password)
    except Exception as exc:
        logger.error("IMAP authentication failed: %s", exc)
        raise

    logger.info("IMAP login successful")
    return client


def _extract_body_text(msg):
    """
    Walk a parsed email.message.EmailMessage and return the plain-text body.

    Falls back to an empty string if no text/plain part is found.
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        return payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        return payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                return payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                return payload.decode("utf-8", errors="replace")
    return ""


def _parse_sender_email(from_header):
    """
    Extract the bare email address from a From header value.

    Examples:
        'John Doe <john@example.com>' -> 'john@example.com'
        'john@example.com'            -> 'john@example.com'
    """
    if not from_header:
        return ""
    # Use email.utils for robust parsing
    from email.utils import parseaddr
    _name, addr = parseaddr(from_header)
    return addr.lower().strip()


# ─── CORE LOGIC ─────────────────────────────────────────────────────────────────

def _fetch_recent_emails(client, days=7):
    """
    Fetch emails from INBOX received within the last *days* days.

    Returns:
        list[dict]: Each dict has keys: uid, from, subject, date, body,
                    in_reply_to, references, message_id
    """
    client.select_folder("INBOX", readonly=True)

    since_date = (datetime.now() - timedelta(days=days)).date()
    logger.info("Searching INBOX for emails since %s", since_date)

    uids = client.search(["SINCE", since_date])
    logger.info("Found %d emails in the last %d days", len(uids), days)

    if not uids:
        return []

    # Fetch relevant parts in a single round-trip
    raw_messages = client.fetch(uids, ["RFC822"])
    results = []

    for uid, data in raw_messages.items():
        raw_email = data.get(b"RFC822")
        if not raw_email:
            continue

        msg = email.message_from_bytes(raw_email, policy=email.policy.default)

        parsed = {
            "uid": uid,
            "from": msg.get("From", ""),
            "sender_email": _parse_sender_email(msg.get("From", "")),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "body": _extract_body_text(msg),
            "in_reply_to": msg.get("In-Reply-To", ""),
            "references": msg.get("References", ""),
            "message_id": msg.get("Message-ID", ""),
        }
        results.append(parsed)

    logger.info("Parsed %d emails", len(results))
    return results


def _load_sent_contacts():
    """
    Load all contacts with status 'Sent' from the Google Sheet.

    Returns:
        list[dict]: Records from the Prospects sheet where Status == 'Sent'.
    """
    from manage_google_sheet import get_prospects_sheet

    logger.info("Loading sent contacts from Google Sheet")
    sheet = get_prospects_sheet()
    all_records = sheet.get_all_records()

    sent_contacts = [
        r for r in all_records
        if r.get("Status") in ("Sent", "Opened")
    ]

    logger.info("Loaded %d sent/opened contacts from sheet", len(sent_contacts))
    return sent_contacts


def _build_contact_lookup(contacts):
    """
    Build lookup structures for matching replies to contacts.

    Returns:
        dict: {
            'by_email': { 'addr@example.com': record, ... },
            'by_subject': { 'normalized subject': record, ... },
        }
    """
    by_email = {}
    by_subject = {}

    for record in contacts:
        contact_email = str(record.get("Contact Email", "")).lower().strip()
        if contact_email:
            by_email[contact_email] = record

        subject = str(record.get("Email Subject", "")).strip().lower()
        if subject:
            by_subject[subject] = record

    return {"by_email": by_email, "by_subject": by_subject}


def _normalize_subject(subject):
    """
    Strip common reply/forward prefixes and whitespace from a subject line.

    'Re: Fw: Re: Hello there' -> 'hello there'
    """
    import re
    cleaned = subject.strip()
    # Repeatedly strip Re:/Fwd:/Fw: prefixes (case-insensitive)
    cleaned = re.sub(r"^(?:re|fwd?)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    # In case of chained prefixes, strip again
    while re.match(r"^(?:re|fwd?)\s*:\s*", cleaned, flags=re.IGNORECASE):
        cleaned = re.sub(r"^(?:re|fwd?)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip().lower()


def _match_replies(emails, contact_lookup):
    """
    Match fetched emails against known campaign contacts.

    Matching logic:
      1. The sender email address must match a contact email in the sheet.
      2. The email must look like a reply: subject starts with "Re:" or
         has an In-Reply-To / References header.

    Args:
        emails: List of parsed email dicts from _fetch_recent_emails.
        contact_lookup: Dict from _build_contact_lookup.

    Returns:
        list[dict]: Matched replies, each with keys:
            sender_email, subject, body, timestamp, company_name, contact_record
    """
    by_email = contact_lookup["by_email"]
    by_subject = contact_lookup["by_subject"]
    matched = []

    for msg in emails:
        sender = msg["sender_email"]
        subject = msg["subject"] or ""
        in_reply_to = msg.get("in_reply_to", "")
        references = msg.get("references", "")

        # --- Strategy 1: Sender email matches a known contact ---
        contact_record = by_email.get(sender)
        if not contact_record:
            continue  # Sender is not a campaign contact; skip

        # Verify this looks like a reply (not just any email from them)
        is_reply = False

        # Check In-Reply-To or References headers
        if in_reply_to or references:
            is_reply = True
            logger.debug(
                "Header-based reply detected from %s (In-Reply-To: %s)",
                sender, in_reply_to
            )

        # Check subject line for Re: prefix and matching original subject
        if not is_reply and subject.lower().startswith("re:"):
            normalized = _normalize_subject(subject)
            original_subject = str(contact_record.get("Email Subject", "")).strip().lower()
            if normalized and original_subject and normalized == original_subject:
                is_reply = True
                logger.debug(
                    "Subject-based reply detected from %s: '%s'",
                    sender, subject
                )
            elif normalized:
                # Looser match: check if normalized subject exists in our lookup
                if normalized in by_subject:
                    contact_record = by_subject[normalized]
                    is_reply = True
                    logger.debug(
                        "Subject-lookup reply detected from %s: '%s'",
                        sender, subject
                    )

        if not is_reply:
            continue

        company_name = contact_record.get("Company Name", "Unknown")
        body_text = msg["body"].strip()

        matched.append({
            "sender_email": sender,
            "subject": subject,
            "body": body_text[:1000],  # Truncate very long bodies
            "timestamp": msg["date"],
            "company_name": company_name,
            "contact_record": contact_record,
        })

        logger.info(
            "Matched reply from %s (%s) - Subject: %s",
            sender, company_name, subject
        )

    return matched


def _update_sheet_for_replies(matched_replies):
    """
    Update the Google Sheet for each matched reply via manage_google_sheet.

    Args:
        matched_replies: List of matched reply dicts from _match_replies.

    Returns:
        int: Number of successfully updated rows.
    """
    from manage_google_sheet import mark_as_replied

    updated = 0
    for reply in matched_replies:
        company = reply["company_name"]
        content = reply["body"][:500]  # match column truncation in manage_google_sheet

        try:
            success = mark_as_replied(company, content)
            if success:
                updated += 1
                logger.info("Marked '%s' as replied in Google Sheet", company)
            else:
                logger.warning(
                    "Could not find '%s' in Google Sheet to mark as replied", company
                )
        except Exception as exc:
            logger.error("Failed to update sheet for '%s': %s", company, exc)

    return updated


# ─── PUBLIC API ──────────────────────────────────────────────────────────────────

def check_for_replies(days=7):
    """
    Main entry point: connect to IMAP, find replies, update Google Sheet.

    Args:
        days: How many days back to search (default 7).

    Returns:
        list[dict]: List of matched replies with keys:
            sender_email, subject, body, timestamp, company_name
    """
    import imapclient  # noqa: F401 - early import check

    client = None
    try:
        # 1. Connect to IMAP
        client = _connect_imap()

        # 2. Fetch recent emails
        emails = _fetch_recent_emails(client, days=days)
        if not emails:
            logger.info("No emails found in the last %d days", days)
            return []

        # 3. Load sent contacts from Google Sheet
        contacts = _load_sent_contacts()
        if not contacts:
            logger.info("No sent/opened contacts in Google Sheet to match against")
            return []

        # 4. Build lookup and match
        lookup = _build_contact_lookup(contacts)
        matched = _match_replies(emails, lookup)
        logger.info("Matched %d replies out of %d emails", len(matched), len(emails))

        # 5. Update Google Sheet
        if matched:
            updated = _update_sheet_for_replies(matched)
            logger.info("Updated %d rows in Google Sheet", updated)

        # 6. Return results (strip contact_record to keep output clean)
        results = []
        for reply in matched:
            results.append({
                "sender_email": reply["sender_email"],
                "subject": reply["subject"],
                "body": reply["body"],
                "timestamp": reply["timestamp"],
                "company_name": reply["company_name"],
            })

        return results

    except EnvironmentError:
        # Missing credentials - re-raise with clear message
        raise
    except Exception as exc:
        logger.error("Unexpected error during reply check: %s", exc, exc_info=True)
        raise
    finally:
        if client:
            try:
                client.logout()
                logger.info("IMAP connection closed")
            except Exception:
                logger.debug("IMAP logout failed (connection may already be closed)")


# ─── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    """CLI interface for checking campaign replies."""
    parser = argparse.ArgumentParser(
        description="Check IMAP inbox for replies to cold email campaign"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed log output to console"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)"
    )

    args = parser.parse_args()

    if args.verbose:
        _enable_console_logging()

    try:
        replies = check_for_replies(days=args.days)

        if not replies:
            print("No campaign replies found.")
        else:
            print(f"Found {len(replies)} campaign replies:")
            for r in replies:
                print(f"  [{r['timestamp']}] {r['company_name']} <{r['sender_email']}>")
                print(f"    Subject: {r['subject']}")
                if args.verbose:
                    preview = r["body"][:200].replace("\n", " ")
                    print(f"    Body: {preview}...")
                print()

        return 0

    except EnvironmentError as exc:
        print(f"CONFIGURATION ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
