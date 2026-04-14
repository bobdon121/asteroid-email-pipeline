#!/usr/bin/env python3
"""
Batch Research Tool - Asteroid.ai Healthcare Prospect Intelligence (Batch Mode)

Researches up to 10 healthcare prospects in a single Claude API call (~50% cost savings
vs. individual calls). Uses the Asteroid.ai Prospect Research Intelligence methodology
(Prompt 1) for deep-dive analysis of each company's portal workflow pain and automation fit.

Output:
  - Individual research JSON files per company (.tmp/research/)
  - Priority matrix table ranking all prospects
  - Top 3 summary for quick-reference
  - Full raw markdown report

Designed to run weekly (Sundays) to prepare the next week's outreach batch.
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
RESEARCH_DIR = PROJECT_ROOT / ".tmp" / "research"
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"

RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT / "tools"))

with open(CONFIG_FILE) as _f:
    _cfg = json.load(_f)
_svc = _cfg.get("service_info", {})
RESEARCH_CONTEXT = _svc.get("research_context", "")


def build_batch_prompt(companies):
    """
    Build the full batch research prompt following the Asteroid.ai Prospect Research
    Intelligence template (Prompt 1), adapted for multiple companies in one call.

    Args:
        companies: List of dicts with keys: company_name, website, contact_name,
                   contact_title, contact_email, industry, description, location,
                   linkedin, country, address

    Returns:
        str: The complete prompt
    """
    prospect_lines = []
    for i, c in enumerate(companies, 1):
        parts = [
            c.get('company_name', ''),
            c.get('website', ''),
            c.get('industry', ''),
            c.get('description', ''),
            c.get('linkedin', ''),
            c.get('country', '') or c.get('location', ''),
            c.get('address', ''),
            c.get('contact_name', ''),
            c.get('contact_title', ''),
            c.get('contact_email', '')
        ]
        prospect_lines.append(f"{i}. {', '.join(p for p in parts if p)}")

    prospects_text = '\n'.join(prospect_lines)

    return f"""You are a senior B2B sales intelligence analyst specializing in healthcare operations and automation. Your job is to produce a deep-dive outreach intelligence report on the list of prospect companies below. This report will be used by Asteroid.ai's sales team to write hyper-personalized warm outreach emails that pitch AI browser agent solutions for healthcare workflow automation.

YOUR GOAL

For each prospect, produce a research brief that gives everything needed to write a warm email that feels like the sender personally spent 30 minutes researching them. The output must be immediately actionable. Every insight should connect to WHY this company would benefit from AI browser agents that automate repetitive portal work without needing APIs.

---

RESEARCH METHODOLOGY (follow this exact sequence for each company)

Step 1 -- Operations & Portal Workflow Audit
- Identify what the company does operationally. Do they interact with payer portals, EHRs, CTMS platforms, government health portals, or other browser-based systems?
- Look for signals of high-volume manual browser work:
  * Do they mention working across multiple payer portals or insurance carriers?
  * Do they handle prior authorizations, coverage verification, claims processing, eligibility checks, or benefits administration?
  * Do they reference EHR integrations, legacy systems, or manual data entry challenges?
  * Do they work with Citrix environments or legacy desktop applications?
  * Do they process fax workflows (sending/receiving clinical documents)?
- Check their tech stack and integration landscape:
  * Do they mention specific EHRs (Epic, Cerner, Athena, legacy/smaller systems)?
  * Do they list payer partnerships or portals they navigate?
  * Do they mention RPA tools (UiPath, Automation Anywhere) or automation challenges?
  * Do they have an API/integration page? (Robust APIs = weaker fit; browser-based portals = strong fit)
- Check for job postings: operations staff, data entry, prior auth specialists, coverage verification analysts, claims processors, rev cycle analysts, medical coders, patient intake coordinators
- Look for existing automation tools, RPA deployments, or AI/ML initiatives

Step 2 -- Company Intelligence
- Recent funding rounds (last 12-18 months): amount, lead investor, total raised
- Recent product launches, partnerships, or major announcements
- Leadership changes (new CEO, COO, VP Ops, VP Engineering hires)
- Geographic expansion, new offices, new payer contracts, or market entry signals
- Hiring activity -- operations/data entry hiring = high manual portal volume; prior auth or rev cycle hiring = active pain point; engineering for "integrations" = struggling with legacy systems; VP/Head of Operations hires = someone coming in to fix operational efficiency
- Customer base size, patient volume, claims volume, or prior auth volume metrics
- Any public statements about portal fragmentation, payer complexity, or administrative burden

Step 3 -- Contact Intelligence
- Verify the contact's current role and title
- Ideal contacts for Asteroid: Head of Operations, VP Operations, VP Engineering/CTO (startups), Head of Revenue Cycle, Director of Prior Auth, COO, CEO (companies under 100 employees), Head of Business Operations, Director of Integrations
- Red flag contacts: VP Legal, VP Marketing, VP Sales (unless very small company), clinical/medical staff without operational authority
- If the provided contact is not ideal, note who would be better and why
- Find personal details: published articles about operational efficiency, podcast appearances about healthcare admin burden, conference talks about automation

Step 4 -- Pitch Angle Construction
- Identify the single strongest use case for Asteroid browser agents at this company (Prior Auth Automation, Coverage Verification, Claims Status, EHR Data Entry Browser, EHR Data Entry Citrix/CUA, Fax Workflows, Voice-to-Browser Pipeline, Clinical Trial Enrollment, Portal Sync, Multi-use)
- Connect a specific business trigger to a specific automation opportunity
- Quantify using these benchmarks:
  * Prior auth: 15-45 min each manually, 2-3 min with Asteroid. 500/day = 150 FTE-hours saved daily
  * Coverage verification: 5-10 min each, under 60 seconds with Asteroid. 1,000/day = 80-160 FTE-hours saved
  * Each FTE doing manual portal work costs ~$40-60K/year. Asteroid can replace 5-20 FTEs per deployment.
- Reference the most relevant Asteroid proof point: Thyme Care (1,000s of daily executions), Vitable Health (10+ carrier portals, self-serve), Moonset Health (10+ hospice EMRs via Citrix), InTouchNow or Delfa (voice-to-browser), Delfa (clinical trials, 30 min to production)

---

OUTPUT FORMAT (follow EXACTLY for each company)

## [NUMBER]. [COMPANY NAME] -- [one-line hook summarizing the browser automation opportunity]

**Contact:** [Full Name], [Title] | **Location:** [City, Country] | **Site:** [domain]

**Operations profile:** [2-4 sentences describing what this company does operationally. What systems do they interact with? What manual browser-based workflows are likely part of their daily operations? Do they work across multiple payer portals? Do they handle prior auths, claims, eligibility? Do they use legacy EHRs or Citrix? What job postings signal manual operations volume?]

**Recent news:** [3-5 sentences covering the most important recent developments. Lead with funding if applicable. Include specific numbers ($, headcount, growth %). Focus on signals indicating growing operational volume, scaling challenges, or manual workflow bottlenecks.]

**Team & hiring signals:** [Employee count if findable. Size of operations team if estimable. Key hires. Call out any operations, prior auth, rev cycle, data entry, or integration engineering hiring. Note contact's background and relevance to an automation buying decision.]

**Best pitch angle:** [3-5 sentences. Identify the PRIMARY use case for Asteroid. Connect to a specific business trigger. Quantify the opportunity using the benchmarks above. Reference the most relevant Asteroid customer proof point. Explain why APIs don't solve this and why RPA breaks.]

**Personalization hooks:**
- [Specific thing #1 to reference in the email opener that proves real research]
- [Specific thing #2]
- [Specific thing #3]

**Primary use case:** [One of: Prior Auth Automation | Coverage Verification | Claims Status | EHR Data Entry (Browser) | EHR Data Entry (Citrix/CUA) | Fax Workflows | Voice-to-Browser Pipeline | Clinical Trial Enrollment | Portal Sync | Multi-use]

**Estimated deal size:** [$3K-6K/mo for startups | $6K-15K/mo for mid-market | $10K-50K/mo for larger ops | $50K-200K+/mo for enterprise]

**Outreach priority: [1-5 stars, written as e.g. 4]**

---

AFTER ALL INDIVIDUAL SECTIONS, ADD:

A quick-reference priority matrix table with these columns:
| Rank | Company | Priority (stars) | Primary use case | Key trigger | Est. deal size | ICP segment |

Sort by priority (highest first).

ICP segment options: Mid-Market Healthcare Ops | Prior Auth / Payer Portal | Digital Health Startup | Enterprise Payer Services / RCM | Hospice / Home Health (Citrix) | Clinical Trial CRO | Voice AI Pipeline Partner

End with a 2-3 sentence summary identifying the top 3 prospects and WHY they are the best targets for Asteroid right now.

---

SCORING CRITERIA FOR OUTREACH PRIORITY

Rate 1 to 5:
- 5 = High-volume portal work confirmed + recent funding or growth + ops team of 20+ doing manual browser tasks + right contact + clear use case matching a proven Asteroid deployment
- 4 = Strong industry fit + clear operational pain + growing team + minor misalignment on contact, timing, or use case specificity
- 3 = Decent fit but lower volume, or already using some automation, or portal work is secondary to core operations
- 2 = Possible fit but requires creative use case, or company primarily uses modern API-first systems, or contact is misaligned
- 1 = Weak fit: fully API-integrated modern systems, no significant portal/browser work, or enterprise with existing RPA vendor lock-in

---

RULES:
1. Think in terms of portal work and browser tasks. Every insight must connect to manual browser-based workflows.
2. Healthcare sub-vertical matters. Prior auth companies, RCM firms, oncology navigation, direct primary care, specialty pharmacy, hospice/home health, clinical trial CROs are Asteroid's sweet spots.
3. Legacy systems = opportunity. Citrix environments, payer portals with no APIs, government health systems are the strongest fits.
4. Hiring = strongest signal. Operations staff, prior auth specialist, coverage verification analyst hiring directly indicate manual portal volume.
5. Quantify the pain. "They do prior auths" is not enough.
6. Reference the right proof point. Match each prospect to the most relevant Asteroid customer.
7. Flag RPA frustration. If a company mentions UiPath or Automation Anywhere, they have tried automation and may be frustrated.
8. No fluff. Every sentence must contain information usable in an email or a go/no-go decision.
9. Be honest about weak fits.
10. Compliance is a feature. Note high-compliance environments. Asteroid's full audit trail is a differentiator.

---

OUR COMPANY CONTEXT:
{RESEARCH_CONTEXT}

---

PROSPECT LIST

{prospects_text}

Research each prospect thoroughly. For each company, investigate operational workflows, portal dependencies, legacy system landscape, manual labor signals (hiring, team size), and the strongest browser automation use case. Quantify the opportunity when possible."""


def parse_batch_response(response_text, companies):
    """
    Parse the batch research response into individual company research dicts.

    Args:
        response_text: Full response from Claude
        companies: Original list of company dicts (for matching)

    Returns:
        tuple: (list of research_data dicts, priority_matrix str, summary str)
    """
    results = []

    # Split into company sections using ## [NUMBER] pattern
    sections = re.split(r'##\s+\d+\.', response_text)
    sections = [s.strip() for s in sections[1:] if s.strip()]

    # Extract priority matrix table
    priority_matrix = ""
    matrix_match = re.search(r'\|.*?Rank.*?\|.*?\n(?:\|.*?\n)+', response_text, re.DOTALL)
    if matrix_match:
        priority_matrix = matrix_match.group(0)

    # Extract summary (text after matrix)
    summary = ""
    summary_match = re.search(
        r'(?:The top three|The three best|The strongest|Top 3 prospects|Summary).*?(?:\n\n|\Z)',
        response_text, re.MULTILINE | re.IGNORECASE | re.DOTALL
    )
    if summary_match:
        summary = summary_match.group(0).strip()

    for i, section in enumerate(sections):
        if i >= len(companies):
            break

        company = companies[i]
        company_name = company.get('company_name', f'Company_{i+1}')

        # Extract fields
        ops_profile = extract_field(section, 'Operations profile')
        recent_news = extract_field(section, 'Recent news')
        team_info = extract_field(section, 'Team & hiring signals')
        pitch_angle_full = extract_field(section, 'Best pitch angle')
        primary_use_case = extract_field(section, 'Primary use case')
        estimated_deal_size = extract_field(section, 'Estimated deal size')
        priority_str = extract_field(section, 'Outreach priority')

        # Parse priority number
        priority = "3"
        if priority_str:
            nums = re.findall(r'(\d)', priority_str)
            if nums:
                priority = nums[0]

        # Extract personalization hooks
        hooks = []
        hooks_match = re.search(
            r'\*\*Personalization hooks:\*\*(.*?)(?:\*\*Primary use case|\*\*Estimated deal|\*\*Outreach priority|\Z)',
            section, re.DOTALL
        )
        if hooks_match:
            for line in hooks_match.group(1).strip().split('\n'):
                line = line.strip().lstrip('- ')
                if line:
                    hooks.append(line)

        # Extract contact info from Contact line
        contact_info = ""
        contact_match = re.search(r'\*\*Contact:\*\*\s*([^|]+)', section)
        if contact_match:
            contact_info = contact_match.group(1).strip().rstrip(',')

        research_data = {
            "company_name": company_name,
            "website": company.get('website', ''),
            "research_text": section.strip(),
            "operations_profile": ops_profile,
            "recent_news": recent_news,
            "team_info": team_info,
            "pitch_angle": pitch_angle_full,
            "personalization_hooks": hooks,
            "primary_use_case": primary_use_case,
            "estimated_deal_size": estimated_deal_size,
            "company_size": "",
            "contact_info": contact_info,
            "priority": priority,
            "researched_at": str(datetime.now()),
            "tokens_used": 0
        }

        results.append(research_data)

    return results, priority_matrix, summary


def extract_field(text, field_name):
    """Extract a bold field value from research text."""
    pattern = rf'\*\*{re.escape(field_name)}[:\*]*\*\*\s*(.*?)(?=\n\*\*|\Z)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def research_batch(companies, save_to_file=True):
    """
    Research a batch of healthcare companies in a single Claude API call.

    Args:
        companies: List of company dicts with keys:
            company_name, website, contact_name, contact_title,
            contact_email, industry, description, location (all optional except company_name)
        save_to_file: Whether to save individual research files

    Returns:
        dict: {
            'results': list of research_data dicts,
            'priority_matrix': str,
            'summary': str,
            'total_tokens': int
        }
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    if not companies:
        print("No companies to research.")
        return {'results': [], 'priority_matrix': '', 'summary': '', 'total_tokens': 0}

    count = len(companies)
    print(f"Batch researching {count} healthcare prospects...")
    for c in companies:
        print(f"  - {c.get('company_name')} ({c.get('website', 'no website')})")

    client = Anthropic(api_key=api_key)
    prompt = build_batch_prompt(companies)

    # ~1200 tokens per company + overhead
    max_tokens = min(count * 1200 + 3000, 16000)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system="You are a senior B2B sales intelligence analyst specializing in healthcare operations and automation. Produce research for Asteroid.ai's sales team. Be specific, factual, and actionable. Every insight should connect to manual browser-based portal work that Asteroid's agents can automate. Follow the output format exactly.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=max_tokens
        )

        response_text = response.content[0].text
        total_tokens = response.usage.input_tokens + response.usage.output_tokens

        print(f"Batch research completed ({total_tokens} tokens used)")

        results, priority_matrix, summary = parse_batch_response(response_text, companies)

        # Distribute token count across companies
        tokens_per = total_tokens // max(len(results), 1)
        for r in results:
            r['tokens_used'] = tokens_per

        if save_to_file:
            from research_company import save_research
            for result in results:
                save_research(result, result['company_name'])

            # Save batch summary JSON
            batch_file = RESEARCH_DIR / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            batch_data = {
                'researched_at': str(datetime.now()),
                'company_count': len(results),
                'total_tokens': total_tokens,
                'priority_matrix': priority_matrix,
                'summary': summary,
                'companies': [r['company_name'] for r in results]
            }
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            print(f"Batch summary saved to: {batch_file}")

            # Save full raw markdown report
            raw_file = RESEARCH_DIR / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_raw.md"
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(response_text)
            print(f"Raw report saved to: {raw_file}")

        return {
            'results': results,
            'priority_matrix': priority_matrix,
            'summary': summary,
            'total_tokens': total_tokens
        }

    except Exception as e:
        print(f"Batch research failed: {str(e)}")
        raise


def main():
    """CLI interface for batch research."""
    import argparse

    parser = argparse.ArgumentParser(description="Batch research healthcare prospects for Asteroid.ai outreach")
    parser.add_argument('--from-sheet', action='store_true', help="Read pending prospects from Google Sheet")
    parser.add_argument('--limit', type=int, default=10, help="Max companies to research (default: 10)")
    parser.add_argument('--update-sheet', action='store_true', help="Write research results back to Google Sheet")
    parser.add_argument('--companies', nargs='+', help="Manual list: 'CompanyName:website.com' pairs")

    args = parser.parse_args()

    try:
        companies = []

        if args.from_sheet:
            from manage_google_sheet import get_pending_companies
            pending = get_pending_companies(limit=args.limit, status_filter="Pending")

            if not pending:
                print("No pending prospects in Google Sheet.")
                return 0

            for p in pending:
                companies.append({
                    'company_name': p.get('Company Name', ''),
                    'website': p.get('Website', ''),
                    'contact_name': p.get('Contact Name', ''),
                    'contact_title': p.get('Contact Title', ''),
                    'contact_email': p.get('Contact Email', ''),
                    'industry': p.get('Industry', ''),
                    'description': p.get('Description', ''),
                    'location': p.get('Location', ''),
                })

        elif args.companies:
            for entry in args.companies:
                if ':' in entry:
                    name, website = entry.split(':', 1)
                    companies.append({'company_name': name.strip(), 'website': website.strip()})
                else:
                    companies.append({'company_name': entry.strip(), 'website': ''})
        else:
            parser.print_help()
            return 1

        result = research_batch(companies)

        print("\n" + "=" * 80)
        print("BATCH RESEARCH SUMMARY")
        print("=" * 80)
        if result['priority_matrix']:
            print("\nPriority Matrix:")
            print(result['priority_matrix'])
        if result['summary']:
            print(f"\n{result['summary']}")
        print(f"\nTotal tokens used: {result['total_tokens']}")
        print(f"Prospects researched: {len(result['results'])}")

        if args.update_sheet and result['results']:
            from manage_google_sheet import update_research_data
            updated = 0
            for r in result['results']:
                time.sleep(2)
                success = update_research_data(r['company_name'], r)
                if success:
                    updated += 1
                    print(f"  Updated sheet: {r['company_name']}")
                else:
                    print(f"  Warning: Could not update sheet for {r['company_name']}")
            print(f"\nUpdated {updated}/{len(result['results'])} prospects in Google Sheet")

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
