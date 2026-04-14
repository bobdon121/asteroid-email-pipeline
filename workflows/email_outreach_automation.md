# Asteroid.ai Cold Email Outreach Pipeline — Workflow SOP

## Purpose

Generate hyper-personalized cold outreach emails for qualified healthcare prospects.
The pipeline researches each company using the Asteroid.ai healthcare intelligence methodology,
then writes a tailored email based on the Asteroid.ai email writer rules.

Nothing is sent automatically. All emails land in Google Sheet columns K & L for manual review before sending.

---

## Required Inputs

| Input | Where |
|---|---|
| Google Sheet with prospects (Status = "Pending") | `config/email_automation_config.json` → `google_sheet_id` |
| `ANTHROPIC_API_KEY` | `.env` |
| Google OAuth credentials | `credentials.json` (from Google Cloud Console) |
| Calendar link | `config/email_automation_config.json` → `service_info.calendar_link` |

---

## Active Tools

| Tool | Purpose |
|---|---|
| `tools/run_email_automation.py` | Main pipeline: research + generate + write to sheet |
| `tools/research_company.py` | Single-company healthcare prospect research (Prompt 1) |
| `tools/research_batch.py` | Batch research up to 10 companies in one API call |
| `tools/generate_email.py` | Asteroid.ai email writer (Prompt 2) |
| `tools/manage_google_sheet.py` | Google Sheet read/write |
| `tools/setup_google_sheet.py` | One-time sheet creation + OAuth setup |

---

## Pipeline (per prospect)

```
Google Sheet (Status = "Pending")
         ↓
Step 1: research_company.py
  - Asteroid.ai Healthcare Intelligence (Prompt 1)
  - 4-step research: Operations Audit → Company Intel → Contact Intel → Pitch Angle
  - Scores prospect 1-5 stars
  - Writes research JSON → Column J
  - Saves to .tmp/research/{company}.json
         ↓
Step 2: generate_email.py
  - Only runs for prospects with >2 stars
  - Validates ICP (Primary / Secondary / Tertiary)
  - Selects best subject line style (A-H, context-aware + randomized)
  - Writes 5-paragraph email (plain text, 140-200 words)
  - Subject → Column K, Body → Column L
  - Saves to .tmp/emails/{company}.txt
         ↓
Step 3: Update status
  - Qualified + email written → Status = "Ready"
  - Priority ≤2 stars or no ICP match → Status = "Disqualified"
```

---

## Google Sheet Column Mapping

| Column | Field | Direction |
|---|---|---|
| A | Company Name | Input |
| B | Website | Input |
| C | Contact Email | Input |
| D | Contact Name | Input |
| E | Contact Title | Input |
| F | Industry / Description | Input |
| G | Location | Input |
| J | Research Brief (JSON) | Written by pipeline |
| K | Email Subject | Written by pipeline |
| L | Email Body | Written by pipeline |
| N | Status | Input: "Pending" / Output: "Ready" or "Disqualified" |

---

## Commands

```bash
# Full pipeline: research + generate emails for all pending prospects
python tools/run_email_automation.py

# Limit to N prospects this run
python tools/run_email_automation.py --max-emails 5

# Preview only (no Claude calls, no sheet writes)
python tools/run_email_automation.py --dry-run

# Skip research (use existing research in column J), only generate emails
python tools/run_email_automation.py --skip-research

# Research a single company (CLI)
python tools/research_company.py --name "Thyme Care" --website "thymecare.com" --contact "John Doe" --title "VP Operations" --save

# Batch research up to 10 companies from Google Sheet
python tools/research_batch.py --from-sheet --limit 10 --update-sheet

# Generate email for a single company using a saved research file
python tools/generate_email.py --company "Thyme Care" --website "thymecare.com" --email "john@thymecare.com" --contact "John" --title "VP Operations" --research-file ".tmp/research/Thyme_Care.json" --save
```

---

## Qualification Rules

- **Minimum priority to receive email:** more than 2 stars (3, 4, or 5)
- **ICP tiers:**
  - Primary: Mid-market healthcare ops (50-500 employees, Series A+) — $6K-$50K/mo
  - Secondary: Enterprise payer services & RCM (500-10,000+ employees) — $50K-$200K+/mo
  - Tertiary: Digital health startups (5-50 employees, Seed-Series B) — $3K-$10K/mo
- Prospects scoring ≤2 stars or failing ICP validation → "Disqualified"

---

## Subject Line Styles (auto-selected per lead)

| Style | Description |
|---|---|
| A | Ops Headcount Challenge (hiring signals) |
| B | Portal Pain (specific EHR/payer portal mention) |
| C | Quantified Waste (FTE-hours, dollar cost) |
| D | Speed to Value (30 min to production) |
| E | Reference Customer Proof (Thyme Care, Vitable, etc.) |
| F | Direct Personal Callout (first name + specific challenge) |
| G | Ironic Contradiction (funding vs. manual ops gap) |
| H | Voice-to-Browser Hook (for AI voice companies) |

---

## Email Structure

1. Pattern Interrupt: specific company detail, proves research, no "Hey"/"Hi"
2. Signal: operational pain quantified (FTE-hours, volume, cost)
3. Proof: matched Asteroid case study (2-3 sentences, facts only)
4. Risk Reduction: low-friction offer tied to their use case
5. CTA: randomized booking link format

Formatting: plain text, 140-200 words, no em dashes, no markdown, no exclamation marks, no bullets

Sign-off:
```
Best,
Yash Tyagi
GTM Lead, Asteroid.ai
```

---

## Status Values

| Status | Meaning |
|---|---|
| Pending | Not yet processed — add new prospects here |
| Ready | Email generated, review cols K & L before sending |
| Disqualified | Priority ≤2 stars or no ICP match — skip |
| Sent | Email manually sent (update this yourself after sending) |

---

## Output Files

| File | Contents |
|---|---|
| `.tmp/research/{company}.json` | Full research JSON per prospect |
| `.tmp/research/batch_*.json` | Batch summary JSON (batch mode) |
| `.tmp/research/batch_*_raw.md` | Full raw markdown report (batch mode) |
| `.tmp/emails/{company}.txt` | Generated email with subject + metadata |
| `.tmp/logs/automation.log` | Run log with status per prospect |

---

## Notes & Learnings
_Update this section as you discover quirks or improvements._
