#!/usr/bin/env python3
"""
Email Generator - Asteroid.ai Healthcare Outbound Email Writer

Generates personalized warm outbound cold emails for qualified healthcare leads
using the Asteroid.ai Email Writer methodology (Prompt 2).

Pipeline:
  1. Qualification filter: skips leads with 2 stars or fewer
  2. ICP validation: Primary / Secondary / Tertiary ICP check
  3. Subject line generation: 1 best-fit line from 8 randomized styles (A-H)
  4. Email body: strict 5-paragraph structure (Pattern Interrupt, Signal, Proof,
     Risk Reduction, CTA)
  5. Output: plain text email ready to send + saved to .tmp/emails/

Formatting rules enforced:
  - No em dashes, no bold/markdown, no exclamation marks, no placeholder brackets
  - No bullet points inside email body
  - 140-200 words per email body (excluding signature)
  - Exact sign-off: "Best,\nYash Tyagi\nGTM Lead, Asteroid.ai"
"""

import os
import sys
import json
import random
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
EMAILS_DIR = PROJECT_ROOT / ".tmp" / "emails"
EMAILS_DIR.mkdir(parents=True, exist_ok=True)

# Load config
_config_path = PROJECT_ROOT / "config" / "email_automation_config.json"
with open(_config_path) as _f:
    _cfg = json.load(_f)

_svc = _cfg.get("service_info", {})
SENDER_NAME = _svc.get("sender_name", "Yash Tyagi")
SENDER_TITLE = _svc.get("sender_title", "GTM Lead, Asteroid.ai")
COMPANY_DETAILS = _svc.get("company_details_prompt", "")
CTA_VARIATIONS = _svc.get("cta_variations", [])
QUALIFICATION_MIN_STARS = _cfg.get("qualification_min_stars", 2)

if not CTA_VARIATIONS:
    CTA_VARIATIONS = [
        "Got 15 minutes this week? Here's my calendar: https://YOUR_CALENDAR_LINK_HERE",
        "Worth a 15-minute call? Here's my calendar: https://YOUR_CALENDAR_LINK_HERE",
        "Would 15 minutes work this week? Happy to walk you through it: https://YOUR_CALENDAR_LINK_HERE",
        "Open to a short walkthrough? Grab a time here: https://YOUR_CALENDAR_LINK_HERE",
        "Worth a quick call? Here's my calendar: https://YOUR_CALENDAR_LINK_HERE",
    ]

# Subject line styles for randomization
SUBJECT_STYLES = {
    'A': 'Ops Headcount Challenge: Frame hiring ops staff as a scaling problem Asteroid solves.\n'
         'Examples: "You\'re hiring 10 ops people. What if you needed 2?" / '
         '"[Company] has 12 open ops roles. There\'s a faster way."',
    'B': 'Portal Pain: Reference the specific pain of working across multiple payer portals or legacy systems.\n'
         'Examples: "Re: [Payer portal] automation" / '
         '"30 minutes to automate your legacy EHR integration" / '
         '"Citrix and legacy EMRs don\'t have to be manual"',
    'C': 'Quantified Waste: Put a dollar figure or time figure on the manual work being done.\n'
         'Examples: "Your ops team shouldn\'t be the bottleneck" / '
         '"150 FTE-hours a day on portal work. That\'s fixable." / '
         '"$780K/year in prior auth labor. Automatable."',
    'D': 'Speed to Value: Lead with Asteroid\'s deployment speed as a pattern interrupt.\n'
         'Examples: "30 minutes to production. Not 6 months." / '
         '"What if [workflow] was automated by Friday?"',
    'E': 'Reference Customer Proof: Name-drop a relevant proof point tied to the lead\'s context.\n'
         'Examples: "How Thyme Care automated 1,000s of daily portal tasks" / '
         '"A clinical trial platform went live in 30 minutes. Here\'s how."',
    'F': 'Direct Personal Callout: Address the contact by first name and reference something specific about their operational challenge.\n'
         'Examples: "[Name], your ops team deserves better than portal copy-paste" / '
         '"[Name], what would your team do with 6 extra hours a day?"',
    'G': 'Ironic Contradiction: Highlight a gap between the company\'s sophistication and their manual operations.\n'
         'Examples: "$82M raised. Still doing prior auth by hand." / '
         '"AI-powered care navigation. Manual fax workflows."',
    'H': 'Voice-to-Browser Hook (for AI voice companies): Position Asteroid as the missing execution layer.\n'
         'Examples: "Your voice AI handles the call. Who handles the system?" / '
         '"The last mile of your voice agent pipeline is still manual."',
}


def get_priority_from_research(research_data):
    """Extract numeric star rating from research data."""
    priority = research_data.get('priority', '')
    if isinstance(priority, str):
        star_count = priority.count('*') or priority.count('\u2605')
        if star_count > 0:
            return star_count
        try:
            return int(priority.strip())
        except (ValueError, AttributeError):
            pass
    elif isinstance(priority, (int, float)):
        return int(priority)
    return 3  # default: assume qualified


def qualifies_for_email(research_data):
    """Check if a prospect qualifies (more than QUALIFICATION_MIN_STARS)."""
    return get_priority_from_research(research_data) > QUALIFICATION_MIN_STARS


def validate_icp(research_data, company_data):
    """
    Validate prospect against Asteroid's three ICP tiers.
    Returns (icp_tier, icp_label) or (None, reason_string).
    """
    ops_profile = research_data.get('operations_profile', '')
    team_info = research_data.get('team_info', '')
    estimated_deal_size = research_data.get('estimated_deal_size', '')
    description = company_data.get('description', '')
    industry = company_data.get('industry', '')
    combined = f"{ops_profile} {team_info} {description} {industry} {estimated_deal_size}".lower()

    # Primary ICP: Mid-Market Healthcare Ops (50-500 employees, Series A+)
    primary_signals = ['payer portal', 'prior auth', 'coverage verification', 'claims', 'ehr',
                       'eligibility', 'rev cycle', 'revenue cycle', 'rcm', 'prior authorization',
                       'fax', 'documo', 'citrix', 'hospice', 'oncology', 'specialty pharmacy',
                       'series a', 'series b', 'series c', '$6k', '$10k', '$15k', '$50k']
    if any(sig in combined for sig in primary_signals):
        return ('primary', 'Mid-Market Healthcare Ops')

    # Secondary ICP: Enterprise Payer Services & RCM
    enterprise_signals = ['enterprise', 'payer', 'health plan', 'insurance carrier',
                          'managed care', '$50k', '$200k', 'large ops', '500 employee',
                          '1,000 employee', '10,000 employee']
    if any(sig in combined for sig in enterprise_signals):
        return ('secondary', 'Enterprise Payer Services / RCM')

    # Tertiary ICP: Digital Health Startups (5-50 employees, Seed-Series B)
    startup_signals = ['startup', 'seed', 'series a', 'clinical trial', 'ctms', 'voice agent',
                       'voice ai', 'ai receptionist', 'healthtech', 'digital health',
                       '$3k', '$6k', '$10k']
    if any(sig in combined for sig in startup_signals):
        return ('tertiary', 'Digital Health Startup')

    # Default: assume tertiary if healthcare-adjacent
    healthcare_signals = ['health', 'medical', 'clinical', 'patient', 'care', 'hospital',
                          'physician', 'provider', 'payer', 'pharmacy', 'dental', 'vision']
    if any(sig in combined for sig in healthcare_signals):
        return ('tertiary', 'Digital Health Startup')

    return (None, 'No clear ICP match')


def select_subject_styles(research_data, company_data):
    """
    Select the best subject line style(s) for this lead based on context.
    Returns a prioritized list of style keys (A-H).
    """
    ops_profile = research_data.get('operations_profile', '').lower()
    recent_news = research_data.get('recent_news', '').lower()
    team_info = research_data.get('team_info', '').lower()
    use_case = research_data.get('primary_use_case', '').lower()
    industry = company_data.get('industry', '').lower()
    description = company_data.get('description', '').lower()
    combined = f"{ops_profile} {recent_news} {team_info} {use_case} {industry} {description}"

    preferred = []

    # H: Voice-to-browser (for voice AI companies)
    if any(x in combined for x in ['voice ai', 'voice agent', 'receptionist', 'intake call', 'ai call']):
        preferred.append('H')

    # G: Ironic contradiction (company has raised significant funding)
    if any(x in combined for x in ['$82m', '$100m', 'series c', 'series d', 'raised', 'funding']):
        preferred.append('G')

    # A: Ops headcount (active ops hiring)
    if any(x in combined for x in ['hiring', 'open role', 'job posting', 'headcount', 'staff']):
        preferred.append('A')

    # C: Quantified waste (prior auth, high volume)
    if any(x in combined for x in ['prior auth', 'coverage verification', '500', '1,000', 'daily']):
        preferred.append('C')

    # B: Portal pain (specific portal/EHR mentions)
    if any(x in combined for x in ['payer portal', 'ehr', 'citrix', 'legacy', 'fax', 'epic', 'cerner']):
        preferred.append('B')

    # D: Speed to value (clinical trial / startup)
    if any(x in combined for x in ['clinical trial', 'startup', 'seed', 'ctms']):
        preferred.append('D')

    # E: Reference customer proof
    if any(x in combined for x in ['thyme', 'vitable', 'moonset', 'delfa', 'intouch']):
        preferred.append('E')

    # Fill remaining with all styles in shuffled order
    all_styles = list('ABCDEFGH')
    random.shuffle(all_styles)
    for s in all_styles:
        if s not in preferred:
            preferred.append(s)

    return preferred


def generate_email(company_data, research_data):
    """
    Generate a personalized warm outbound email for a healthcare prospect.

    Args:
        company_data: Dict with company_name, website, contact_email, contact_name,
                      contact_title, description, industry, location
        research_data: Research dict from research_company.py (research_text, pitch_angle,
                       personalization_hooks, priority, primary_use_case, etc.)

    Returns:
        dict: {
            'subject': str,
            'body': str,
            'qualified': bool,
            'priority': int,
            'icp_tier': str,
            'use_case': str,
        }
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    priority = get_priority_from_research(research_data)
    qualified = priority > QUALIFICATION_MIN_STARS

    if not qualified:
        company_name = company_data.get('company_name', 'Unknown')
        print(f"SKIPPED: {company_name} — Priority {priority} stars (needs >{QUALIFICATION_MIN_STARS})")
        return {
            'subject': '',
            'body': '',
            'qualified': False,
            'priority': priority,
            'icp_tier': None,
            'use_case': research_data.get('primary_use_case', '')
        }

    # ICP validation
    icp_tier, icp_label = validate_icp(research_data, company_data)
    if icp_tier is None:
        company_name = company_data.get('company_name', 'Unknown')
        print(f"SKIPPED: {company_name} — {icp_label}")
        return {
            'subject': '',
            'body': '',
            'qualified': False,
            'priority': priority,
            'icp_tier': None,
            'use_case': research_data.get('primary_use_case', '')
        }

    # Select subject line style(s)
    style_order = select_subject_styles(research_data, company_data)
    primary_style = style_order[0]
    secondary_style = style_order[1]
    primary_style_desc = SUBJECT_STYLES[primary_style]
    secondary_style_desc = SUBJECT_STYLES[secondary_style]

    # Randomize CTA
    selected_cta = random.choice(CTA_VARIATIONS)

    # Build context for Claude
    contact_name = company_data.get('contact_name', '')
    first_name = contact_name.split()[0] if contact_name else 'there'
    contact_title = company_data.get('contact_title', '')

    research_text = research_data.get('research_text', '')
    ops_profile = research_data.get('operations_profile', '')
    recent_news = research_data.get('recent_news', '')
    team_info = research_data.get('team_info', '')
    pitch_angle = research_data.get('pitch_angle', '')
    use_case = research_data.get('primary_use_case', '')
    estimated_deal_size = research_data.get('estimated_deal_size', '')

    hooks = research_data.get('personalization_hooks', [])
    hooks_text = '\n'.join(f"- {h}" for h in hooks) if isinstance(hooks, list) else str(hooks)

    description = company_data.get('description', '')
    description_line = f"\nCompany Description: {description}" if description else ""

    prompt = f"""You are a senior outbound growth strategist and email copywriter for Asteroid.ai, a YC-backed AI automation platform for healthcare. You write warm, personalized outbound emails for qualified healthcare leads.

You are disciplined, observant, and never fabricate information. You only write what the research data supports. You understand healthcare operations deeply and speak the language of ops leaders, rev cycle managers, and healthtech CTOs.

---

YOUR IDENTITY

You are writing on behalf of:
Name: {SENDER_NAME}
Title: {SENDER_TITLE}

Sign-off format (use exactly):
Best,
{SENDER_NAME}
{SENDER_TITLE}

---

RESEARCH DOCUMENT FOR THIS LEAD:

Company: {company_data.get('company_name')}
Website: {company_data.get('website')}
Contact: {contact_name}{f', {contact_title}' if contact_title else ''}
Contact Email: {company_data.get('contact_email', '')}{description_line}
Priority Rating: {priority} stars
ICP Tier: {icp_label}
Primary Use Case: {use_case}
Estimated Deal Size: {estimated_deal_size}

Operations Profile:
{ops_profile}

Recent News:
{recent_news}

Team & Hiring Signals:
{team_info}

Pitch Angle:
{pitch_angle}

Personalization Hooks:
{hooks_text}

Full Research:
{research_text}

---

{COMPANY_DETAILS}

---

STEP 1: SUBJECT LINE GENERATION

Generate exactly 1 subject line. Use the style that best fits this lead's specific situation.

PREFERRED STYLE FOR THIS LEAD: Style {primary_style}
{primary_style_desc}

FALLBACK STYLE (use if preferred doesn't produce a strong line): Style {secondary_style}
{secondary_style_desc}

Rules for subject lines:
- Never use em dashes. Ever.
- Keep under 60 characters when possible.
- Every subject line must reference real data from the research document. No generic lines.
- Pick ONE style. Commit to it.

---

STEP 2: EMAIL BODY

Write the email body following this EXACT 5-paragraph structure. No exceptions.

Paragraph 1: Pattern Interrupt (1-2 lines max)
- Address {first_name} by first name followed by a comma. Never use "Hey" or "Hi".
- Reference something specific and observant about their company: a recent funding round, a product launch, a hiring surge, a public statement about scaling.
- This must come directly from the research document.
- Goal: make them feel seen, not sold to.

Paragraph 2: Signal (The Operational Pain)
- Identify the specific manual, browser-based workflow that is costing them time and money.
- Reference concrete signals from the research document: ops team size, number of portals they work across, volume of daily tasks, hiring for ops roles, legacy systems in use.
- Quantify the pain when possible: "At 500 submissions a day, that is 150+ FTE-hours on portal work alone."
- Connect the pain to a business consequence: linear headcount scaling, error rates, missed appeal windows, slow patient enrollment, compliance risk.
- Do NOT pitch Asteroid in this paragraph. Just describe the problem with specificity.

Paragraph 3: Proof (Asteroid's Relevant Capability)
- Reference the Asteroid capability or case study most relevant to this lead's situation.
- Only use facts from the Asteroid Company Details section above.
- Match the proof to the lead's context:
  * Prior auth pain? Reference the self-healing browser agents that work across any payer portal.
  * Legacy EHR/Citrix? Reference Moonset Health (10+ hospice EMRs via Citrix).
  * Small eng team needing integrations? Reference Delfa (30 minutes to production, 95% engineering effort saved).
  * High-volume ops? Reference Thyme Care (1,000s of daily executions).
  * Coverage verification? Reference Vitable Health (self-serve across 10+ carrier portals, no engineering needed).
  * Voice AI company? Reference InTouchNow or Delfa voice-to-browser pipeline.
  * Fax workflows? Reference Thyme Care's Documo automation.
- Keep it to 2-3 sentences. Be specific, not salesy.

Paragraph 4: Risk Reduction (Low-Friction Offer)
- Offer something tangible and low-commitment: a live demo on their actual workflow, a quick walkthrough of a relevant case study, or a 15-minute technical overview.
- Frame it around their specific use case, not a generic product demo.
- One to two sentences max.

Paragraph 5: CTA (Call Booking)
- End with this exact CTA: {selected_cta}

---

FORMATTING RULES (STRICT):
- Never use em dashes. Ever. Use periods, commas, or restructure the sentence instead.
- No bold, italics, or markdown formatting inside the email body. Plain text only.
- Word count: 140-200 words max for the email body (excluding signature).
- Tone: warm, observant, consultative. Never salesy, never desperate, never hype-driven.
- No exclamation marks except in very rare cases where genuine excitement is warranted.
- No placeholder brackets in the final email. Every detail must be filled in from the research.
- No bullet points or lists inside the email body. Write in natural paragraphs.
- Parentheses are okay for brief clarifications but use sparingly.
- Do NOT hallucinate or invent any data not in the research document.
- Never reference Asteroid capabilities not listed in the Asteroid Company Details above.
- Sell speed to value. "30 minutes to production" and "self-serve with no engineering" are disruptive claims in healthcare.
- Position compliance as a feature. Every Asteroid execution has a full audit trail. HIPAA compliance is built in.
- Always lead with the prospect's pain, not the product.

---

PITCH ANGLE STRATEGY (read before writing):

1. Large ops teams doing manual portal work = direct replacement. Lead with Thyme Care or quantify FTE savings.
2. Hiring for ops roles = scaling pain. Frame it as: "What if you needed 2 instead of 10?"
3. Prior auth volume = biggest pain point. Quantify: 15-45 min per submission, 10-25% denial rates, $780K/year savings at 500/day.
4. Legacy EHRs or Citrix = no competition. Lead with Moonset Health. This is a moat.
5. Small eng team needing legacy integrations = speed play. Lead with Delfa (30 min to production, 95% eng effort saved).
6. AI voice company in healthcare = voice-to-browser pipeline. Lead with InTouchNow or Delfa.
7. Recent funding = budget and urgency. Frame Asteroid as the way to decouple growth from hiring.
8. Multi-payer portal complexity = horizontal scaling. Lead with Vitable (10+ carrier portals, self-serve, no engineering).

Do NOT pitch: website design, marketing services, CMS migration, SEO, general AI/ML consulting, or anything not directly related to browser-based or desktop workflow automation.

---

OUTPUT FORMAT (follow exactly):

SUBJECT: [single best-fit subject line]

EMAIL BODY:
[Full 5-paragraph email text here]

Best,
{SENDER_NAME}
{SENDER_TITLE}"""

    client = Anthropic(api_key=api_key)

    company_name = company_data.get('company_name', 'Unknown')
    print(f"Generating email for {company_name} (Priority: {priority} stars | ICP: {icp_label} | Use case: {use_case})...")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        email_content = response.content[0].text

        # Parse response
        subject = ""
        body = ""
        body_lines = []
        in_body = False

        for line in email_content.strip().split('\n'):
            stripped = line.strip()

            if stripped.startswith("SUBJECT:"):
                subject = stripped.replace("SUBJECT:", "").strip().strip('"').strip("'")
                continue

            if stripped.startswith("EMAIL BODY:"):
                in_body = True
                continue

            if in_body:
                body_lines.append(line)

        body = '\n'.join(body_lines).strip()

        # Fallback subject parsing
        if not subject:
            for line in email_content.strip().split('\n'):
                if line.strip().lower().startswith("subject:"):
                    subject = line.strip()[8:].strip().strip('"').strip("'")
                    break

        result = {
            'subject': subject,
            'body': body,
            'qualified': True,
            'priority': priority,
            'icp_tier': icp_tier,
            'icp_label': icp_label,
            'use_case': use_case,
            'style_used': primary_style,
        }

        print(f"Email generated — Subject: {subject}")
        return result

    except Exception as e:
        print(f"Email generation failed: {str(e)}")
        raise


def save_email(email_data, company_name):
    """Save generated email to .txt file."""
    safe_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')

    filename = EMAILS_DIR / f"{safe_name}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Company: {company_name}\n")
        f.write(f"Subject: {email_data.get('subject', '')}\n")
        f.write(f"Priority: {email_data.get('priority', 'N/A')} stars\n")
        f.write(f"ICP: {email_data.get('icp_label', 'N/A')}\n")
        f.write(f"Use Case: {email_data.get('use_case', 'N/A')}\n")
        f.write(f"Qualified: {email_data.get('qualified', False)}\n\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"SUBJECT: {email_data.get('subject', '')}\n\n")
        f.write(email_data.get('body', ''))

    print(f"Email saved to: {filename}")
    return filename


def main():
    """CLI interface for single-company email generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate Asteroid.ai cold email for a healthcare prospect")
    parser.add_argument('--company', required=True, help="Company name")
    parser.add_argument('--website', required=True, help="Company website")
    parser.add_argument('--email', required=True, help="Contact email")
    parser.add_argument('--contact', default='', help="Contact name")
    parser.add_argument('--title', default='', help="Contact title")
    parser.add_argument('--research-file', help="Path to research JSON file from research_company.py")
    parser.add_argument('--save', action='store_true', help="Save email to .tmp/emails/")
    parser.add_argument('--update-sheet', action='store_true', help="Update Google Sheet with email")

    args = parser.parse_args()

    try:
        if args.research_file:
            with open(args.research_file, 'r', encoding='utf-8') as f:
                research_data = json.load(f)
        else:
            research_data = {'research_text': 'No research available', 'priority': '3'}

        company_data = {
            'company_name': args.company,
            'website': args.website,
            'contact_email': args.email,
            'contact_name': args.contact,
            'contact_title': args.title,
        }

        email_data = generate_email(company_data, research_data)

        if not email_data.get('qualified'):
            print(f"\nLead not qualified (Priority: {email_data.get('priority')} stars, needs >{QUALIFICATION_MIN_STARS})")
            return 0

        print("\n" + "=" * 80)
        print(f"SUBJECT: {email_data['subject']}")
        print("=" * 80)
        print(email_data['body'])
        print("=" * 80)

        if args.save:
            save_email(email_data, args.company)

        if args.update_sheet:
            sys.path.insert(0, str(PROJECT_ROOT / "tools"))
            from manage_google_sheet import update_email_content
            success = update_email_content(
                args.company,
                email_data['subject'],
                email_data['body'],
                'asteroid-outreach-v1'
            )
            if success:
                print("Updated Google Sheet")

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
