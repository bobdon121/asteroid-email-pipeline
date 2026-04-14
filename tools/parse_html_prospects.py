#!/usr/bin/env python3
"""
Parse HTML prospects from saved ChatGPT conversation.
Extracts company data and loads into Google Sheets (Prospects tab) with Status = "Pending".

Uses manage_google_sheet.py's add_company() function for sheet operations.
Only extracts ONE contact per company, preferring CEO/Founder/CTO titles.
"""

import re
import sys
import html
import time
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))
from manage_google_sheet import add_company, get_prospects_sheet

# Target titles in priority order (highest priority first)
TITLE_PRIORITY = [
    "ceo", "founder", "co-founder", "cto", "cmo",
    "vp of marketing", "vp of product",
    "head of marketing", "head of design", "head of product", "head of digital",
    "director of marketing", "director of product",
    "creative director",
    "president", "chairman",
    "chief"  # catch-all for C-suite
]

HTML_FILE = Path(r"c:\Users\Lenovo\Downloads\CSV Data Extraction.html")


def title_priority(title: str) -> int:
    """Return priority score for a title (lower = better). Returns 999 if no match."""
    title_lower = title.lower()
    for i, keyword in enumerate(TITLE_PRIORITY):
        if keyword in title_lower:
            return i
    return 999


def decode(text: str) -> str:
    """Decode HTML entities."""
    return html.unescape(text).strip()


def extract_prospects(filepath: Path) -> list:
    """Extract all unique prospects from the HTML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip HTML tags to get plain text lines
    text = re.sub(r'<[^>]+>', '\n', content)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    companies = {}  # keyed by website domain to deduplicate

    # ─── SECTION 1: Compact table (lines ~204-302, the expanded version) ────────
    # Format: Name, Website, Industry, Description(s), LinkedIn, Country, Address, Contact, Title, Email
    # We'll parse the second (expanded) table which has better descriptions.
    # Each company block starts at a known pattern.

    # Parse section 2 (expanded table, lines 204-302 approx)
    i = 0
    while i < len(lines):
        # Look for the expanded table entries (after "Complete Extracted Data" header)
        # These follow the pattern: Name on one line, domain on next, industry on next, etc.
        # We detect by checking if a line looks like a domain and is preceded by a company name
        if (lines[i] == "Complete Extracted Data" or
            (i > 190 and i < 310 and lines[i].endswith('.com') or
             lines[i].endswith('.ai') or lines[i].endswith('.io') or
             lines[i].endswith('.co'))):

            if lines[i] == "Complete Extracted Data":
                i += 1  # skip header row labels (Name, Website, Industry, etc.)
                # Skip the column headers
                while i < len(lines) and lines[i] in ["Name", "Website", "Industry", "Description",
                                                        "LinkedIn URL", "Country", "Address",
                                                        "Contact Name", "Contact Title", "Contact Email"]:
                    i += 1
                continue

            # Check if this is actually a website domain (in the right range)
            if i > 200 and i < 310:
                website = decode(lines[i])
                # The company name should be the line before
                company_name = decode(lines[i - 1])

                # Skip if it's a column header or navigation text
                if company_name in ["Name", "Website", "Industry", "Contact Name"]:
                    i += 1
                    continue

                industry = decode(lines[i + 1]) if i + 1 < len(lines) else ""
                # Description might span multiple lines, find LinkedIn URL to know where it ends
                desc_lines = []
                j = i + 2
                while j < len(lines) and not lines[j].startswith("http://www.linkedin.com"):
                    desc_lines.append(decode(lines[j]))
                    j += 1
                # Skip linkedin, country, address
                j += 1  # skip LinkedIn
                country = decode(lines[j]) if j < len(lines) else ""
                j += 1  # skip country
                j += 1  # skip address
                contact_name = decode(lines[j]) if j < len(lines) else ""
                j += 1
                contact_title = decode(lines[j]) if j < len(lines) else ""
                j += 1
                contact_email = decode(lines[j]) if j < len(lines) else ""

                if website and "@" in contact_email:
                    companies[website] = {
                        "company_name": company_name,
                        "website": website,
                        "industry": industry,
                        "contact_name": contact_name,
                        "contact_title": contact_title,
                        "contact_email": contact_email,
                    }
                i = j + 1
                continue

        i += 1

    # ─── SECTION 3: Labeled format with "Website:", "Industry:", etc. (lines 343+) ────
    # Format uses emoji numbered headers like "1️⃣ Payrails"
    # Each company block has Website:, Industry:, Company Description, Contacts section

    i = 330
    while i < len(lines) and i < 600:
        line = lines[i]

        # Detect company header (emoji number + name pattern)
        emoji_match = re.match(r'^[\d️⃣🔟]+\s*(.+)$', line)
        if not emoji_match and re.match(r'^[0-9].*[A-Z]', line):
            # Try alternate: "1️⃣ Company Name" where emoji gets mangled
            pass

        # Better: detect by "Website:" pattern
        if line == "Website:" or line.startswith("Website:"):
            # Company name is a few lines above (look for the emoji header)
            company_name = ""
            for back in range(1, 8):
                candidate = lines[i - back] if i - back >= 0 else ""
                # The company header line has emoji prefix
                if any(c in candidate for c in "️⃣🔟") or re.match(r'^\d+\s', candidate):
                    # Clean emoji prefix
                    company_name = re.sub(r'^[\d️⃣🔟\s]+', '', candidate).strip()
                    break
                # Or it might just be a clean name after "Contacts" section of previous company
                if candidate and candidate not in ["Contacts", "Company Description", "Location:",
                                                     "LinkedIn:", "Email:", "Title:"] and \
                   not candidate.startswith("http") and "@" not in candidate and \
                   len(candidate) > 2 and not candidate.startswith("Location:"):
                    # Could be the company name
                    pass

            # Get website from next line
            if line == "Website:":
                i += 1
                website = decode(lines[i]) if i < len(lines) else ""
            else:
                website = decode(line.replace("Website:", "").strip())

            # Get industry
            i += 1
            if i < len(lines) and lines[i] == "Industry:":
                i += 1
                industry = decode(lines[i]) if i < len(lines) else ""
            else:
                industry = ""

            # Skip to Contacts section
            contacts = []
            while i < len(lines) and lines[i] != "Contacts":
                if "(No contacts listed" in lines[i]:
                    break
                i += 1

            if i < len(lines) and lines[i] == "Contacts":
                i += 1
                # Parse contacts until we hit next company or end marker
                while i < len(lines):
                    # Check if this is a contact name (not a label)
                    if lines[i].startswith("Title:"):
                        i += 1
                        continue
                    if lines[i].startswith("Email:"):
                        i += 1
                        continue
                    if lines[i].startswith("LinkedIn:"):
                        i += 1
                        continue
                    if lines[i].startswith("Location:"):
                        i += 1
                        continue
                    if lines[i].startswith("http"):
                        i += 1
                        continue

                    # Check if we've hit the next company or end section
                    if any(c in lines[i] for c in "️⃣🔟") or lines[i].startswith("If you want"):
                        break

                    # This might be a contact name
                    contact_name_candidate = decode(lines[i])
                    i += 1

                    # Next should be "Title: ..."
                    if i < len(lines) and lines[i].startswith("Title:"):
                        contact_title = decode(lines[i].replace("Title:", "").strip())
                        i += 1
                        # Next should be "Email:" then the actual email
                        if i < len(lines) and lines[i] == "Email:":
                            i += 1
                            contact_email = decode(lines[i]) if i < len(lines) else ""
                            i += 1
                            contacts.append({
                                "name": contact_name_candidate,
                                "title": contact_title,
                                "email": contact_email,
                            })
                            # Skip LinkedIn and Location
                            while i < len(lines) and (lines[i].startswith("LinkedIn:") or
                                                       lines[i].startswith("http") or
                                                       lines[i].startswith("Location:")):
                                i += 1
                            continue

                    # Not a contact pattern, might be end of contacts
                    break

            # Pick the best contact based on title priority
            if contacts and company_name:
                best = min(contacts, key=lambda c: title_priority(c["title"]))
                companies[website] = {
                    "company_name": company_name,
                    "website": website,
                    "industry": industry,
                    "contact_name": best["name"],
                    "contact_title": best["title"],
                    "contact_email": best["email"],
                }

        i += 1

    # For section 1 companies, also apply title priority if we have section 3 data
    # (section 3 won't overlap with section 1 companies since they're different sets)

    return list(companies.values())


def load_to_sheets(prospects: list) -> int:
    """Load prospects into Google Sheets, skipping duplicates. Returns count loaded."""
    # Get existing companies to avoid duplicates
    sheet = get_prospects_sheet()
    existing = sheet.get_all_records()
    existing_websites = {r.get("Website", "").lower().strip() for r in existing}
    existing_emails = {r.get("Contact Email", "").lower().strip() for r in existing}

    loaded = 0
    skipped = 0
    for p in prospects:
        website = p["website"].lower().strip()
        email = p["contact_email"].lower().strip()

        if website in existing_websites or email in existing_emails:
            print(f"  SKIP (duplicate): {p['company_name']} ({website})")
            skipped += 1
            continue

        print(f"  ADD: {p['company_name']} | {p['website']} | {p['contact_name']} ({p['contact_title']}) | {p['contact_email']} | {p['industry']}")
        try:
            add_company(
                company_name=p["company_name"],
                website=p["website"],
                contact_email=p["contact_email"],
                contact_name=p["contact_name"],
                industry=p["industry"],
            )
            existing_websites.add(website)
            existing_emails.add(email)
            loaded += 1
            time.sleep(1.5)  # Rate limit: avoid Google Sheets API quota
        except Exception as e:
            print(f"  ERROR adding {p['company_name']}: {e}")

    return loaded, skipped


def main():
    print(f"Parsing HTML file: {HTML_FILE}")
    prospects = extract_prospects(HTML_FILE)

    print(f"\nExtracted {len(prospects)} unique prospects:")
    print("-" * 80)
    for p in prospects:
        print(f"  {p['company_name']:30s} | {p['website']:25s} | {p['contact_name']:25s} | {p['contact_title']}")
    print("-" * 80)

    print(f"\nLoading {len(prospects)} prospects into Google Sheets...")
    loaded, skipped = load_to_sheets(prospects)
    print(f"\nDone! Loaded: {loaded}, Skipped (duplicates): {skipped}")


if __name__ == "__main__":
    main()
