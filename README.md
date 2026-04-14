# Asteroid.ai Cold Email Pipeline

Automated healthcare prospect research and personalized cold email generation for Asteroid.ai (YC-backed AI browser agents for healthcare workflow automation).

Built on the **WAT framework** (Workflows, Agents, Tools) — AI handles reasoning, Python handles execution.

## What It Does

1. Reads prospects from Google Sheet (Status = "Pending")
2. Researches each company using the Asteroid.ai healthcare intelligence methodology
3. Generates a personalized 5-paragraph cold email per qualified prospect
4. Writes subject + body back to the sheet for manual review and send

**Nothing is sent automatically.** You review and send manually.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and Google OAuth credentials
```

### 3. Set up Google Sheet (first time only)

```bash
python tools/setup_google_sheet.py
# Follow OAuth prompts, then paste the Sheet ID into config/email_automation_config.json
```

### 4. Update config

Edit `config/email_automation_config.json`:
- Set `google_sheet_id`
- Set `service_info.calendar_link` (your Calendly/Cal.com link)

### 5. Add prospects to Google Sheet

Fill columns A (Company Name), B (Website), C (Contact Email), D (Contact Name), E (Contact Title), N (Status = "Pending").

### 6. Run the pipeline

```bash
# Full run: research + generate emails for all pending prospects
python tools/run_email_automation.py

# Limit to 5 prospects
python tools/run_email_automation.py --max-emails 5

# Preview without Claude calls
python tools/run_email_automation.py --dry-run
```

## Project Structure

```
├── tools/
│   ├── run_email_automation.py    # Main pipeline orchestrator
│   ├── research_company.py        # Single-company research (Prompt 1)
│   ├── research_batch.py          # Batch research up to 10 companies
│   ├── generate_email.py          # Email writer (Prompt 2)
│   ├── manage_google_sheet.py     # Google Sheets read/write
│   └── setup_google_sheet.py      # One-time OAuth + sheet creation
├── config/
│   └── email_automation_config.json  # Asteroid.ai settings, sender info, CTAs
├── workflows/
│   └── email_outreach_automation.md  # Full pipeline SOP
├── .tmp/
│   ├── research/                  # Research JSON files per prospect
│   ├── emails/                    # Generated email .txt files
│   └── logs/                      # Run logs
├── .env                           # API keys (gitignored)
├── .env.example                   # Environment variable template
└── CLAUDE.md                      # Agent instructions (WAT framework)
```

## Qualification Rules

- Prospects scoring more than 2 stars receive an email
- Prospects scoring 2 stars or fewer are marked "Disqualified" automatically
- ICP validation: Primary (mid-market ops), Secondary (enterprise RCM), Tertiary (digital health startup)

## Security

- Never commit `.env`, `credentials.json`, or `token.pickle`
- Store all secrets in `.env` only

---

For full pipeline documentation, see [workflows/email_outreach_automation.md](workflows/email_outreach_automation.md)
For agent instructions, see [CLAUDE.md](CLAUDE.md)
