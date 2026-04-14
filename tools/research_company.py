#!/usr/bin/env python3
"""
Company Research Tool - Asteroid.ai Healthcare Prospect Intelligence

Uses Claude to produce deep-dive B2B sales intelligence reports on healthcare prospects.
Based on the Asteroid.ai Prospect Research Intelligence methodology (Prompt 1):
  - Step 1: Operations & Portal Workflow Audit
  - Step 2: Company Intelligence
  - Step 3: Contact Intelligence
  - Step 4: Pitch Angle Construction

Output feeds directly into generate_email.py for personalized cold outreach.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
RESEARCH_DIR = PROJECT_ROOT / ".tmp" / "research"
CONFIG_FILE = PROJECT_ROOT / "config" / "email_automation_config.json"

RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_FILE) as _f:
    _cfg = json.load(_f)
_svc = _cfg.get("service_info", {})
COMPANY_DETAILS = _svc.get("company_details_prompt", "")
RESEARCH_CONTEXT = _svc.get("research_context", "")


def build_research_prompt(company_name, website, contact_name="", contact_title="", industry="", description="", location=""):
    """Build the Asteroid.ai healthcare prospect research prompt (Prompt 1)."""

    contact_block = ""
    if contact_name:
        contact_block = f"\n- Contact: {contact_name}"
        if contact_title:
            contact_block += f", {contact_title}"

    extra_block = ""
    if industry:
        extra_block += f"\n- Industry: {industry}"
    if description:
        extra_block += f"\n- Description: {description}"
    if location:
        extra_block += f"\n- Location: {location}"

    return f"""You are a senior B2B sales intelligence analyst specializing in healthcare operations and automation. Produce a deep-dive outreach intelligence report on this prospect company. This report will be used by Asteroid.ai's sales team to write hyper-personalized warm outreach emails that pitch AI browser agent solutions for healthcare workflow automation.

PROSPECT:
- Company: {company_name}
- Website: {website}{contact_block}{extra_block}

YOUR GOAL

Produce a research brief that gives everything needed to write a warm email that feels like the sender personally spent 30 minutes researching this company. Every insight must connect to WHY this company would benefit from AI browser agents that automate repetitive portal work without needing APIs.

---

RESEARCH METHODOLOGY (follow this exact sequence)

Step 1 -- Operations & Portal Workflow Audit
- Visit the company website and identify what they do operationally. Do they interact with payer portals, EHRs, CTMS platforms, government health portals, or other browser-based systems?
- Look for signals of high-volume manual browser work:
  * Do they mention working across multiple payer portals or insurance carriers?
  * Do they handle prior authorizations, coverage verification, claims processing, eligibility checks, or benefits administration?
  * Do they reference EHR integrations, legacy systems, or manual data entry challenges?
  * Do they work with Citrix environments or legacy desktop applications?
  * Do they process fax workflows (sending/receiving clinical documents)?
- Check their tech stack and integration landscape:
  * Do they mention specific EHRs they work with (Epic, Cerner, Athena, legacy/smaller systems)?
  * Do they list payer partnerships or portals they navigate?
  * Do they mention RPA tools (UiPath, Automation Anywhere) or automation challenges?
  * Do they have an API/integration page? (Robust APIs = weaker fit; browser-based portals = strong fit)
- Check for job postings related to: operations staff, data entry, prior auth specialists, coverage verification analysts, claims processors, rev cycle analysts, medical coders, patient intake coordinators
- Look for any existing automation tools, RPA deployments, or AI/ML initiatives

Step 2 -- Company Intelligence
- Recent funding rounds (last 12-18 months): amount, lead investor, total raised
- Recent product launches, partnerships, or major announcements
- Leadership changes (new CEO, COO, VP Ops, VP Engineering hires)
- Geographic expansion, new offices, new payer contracts, or market entry signals
- Hiring activity: ops/data entry hiring = high manual portal volume; prior auth or rev cycle hiring = active pain point; engineering hiring for "integrations" = struggling with legacy systems; VP/Head of Operations hires = someone coming in to fix operational efficiency
- Customer base size, patient volume, claims volume, or prior auth volume metrics
- Any public statements about portal fragmentation, payer complexity, or administrative burden

Step 3 -- Contact Intelligence
- Verify the contact's current role and title
- Ideal contacts for Asteroid: Head of Operations, VP Operations, VP Engineering/CTO (startups), Head of Revenue Cycle, Director of Prior Auth, COO, CEO (companies <100 employees), Head of Business Operations, Director of Integrations
- Red flag contacts: VP Legal, VP Marketing, VP Sales (unless very small company), clinical/medical staff without operational authority
- If the provided contact is not ideal, note who would be better and why
- Find personal details: published articles about operational efficiency, podcast appearances about healthcare admin burden, conference talks about automation, LinkedIn posts about hiring challenges or manual workflow frustrations

Step 4 -- Pitch Angle Construction
- Identify the single strongest use case for Asteroid browser agents at this company:
  * Prior authorization automation: automating PA submissions, document uploads, and status tracking across payer portals (Asteroid's #1 validated use case, $31B+ market)
  * Coverage verification / eligibility checks: automating insurance verification across 10+ carrier portals (proven by Vitable Health)
  * Claims status checking: batch checking claim statuses across payer portals, flagging denials for immediate action
  * EHR data entry & retrieval: automating data entry into legacy EHRs that lack APIs, including Citrix-based systems (proven by Moonset Health)
  * Fax workflow automation: automating fax sending/receiving and document processing via platforms like Documo (proven by Thyme Care)
  * Voice-to-browser pipeline: completing the "last mile" after an AI voice agent handles a call (proven by InTouchNow and Delfa)
  * Clinical trial enrollment: automating patient screening and enrollment in legacy CTMS platforms (proven by Delfa)
  * Portal updates & data sync: keeping data synchronized across multiple portals and systems
- Connect a specific business trigger (funding, scaling ops team, new payer contracts, growing patient volume) to a specific automation opportunity
- Quantify the opportunity:
  * Prior auth: 15-45 min each manually, 2-3 min with Asteroid. 500/day = 150 FTE-hours saved daily
  * Coverage verification: 5-10 min each, under 60 seconds with Asteroid. 1,000/day = 80-160 FTE-hours saved
  * Each FTE doing manual portal work costs ~$40-60K/year. Asteroid can replace 5-20 FTEs per deployment.
- Frame in terms of business outcomes: headcount savings, faster turnaround, reduced denial rates, ability to scale without linear hiring

---

OUTPUT FORMAT (follow EXACTLY):

**Operations profile:** [2-4 sentences describing what this company does operationally. What systems do they interact with? What manual browser-based workflows are likely part of their daily operations? Do they work across multiple payer portals? Do they handle prior auths, claims, eligibility? Do they use legacy EHRs or Citrix? What job postings signal manual operations volume?]

**Recent news:** [3-5 sentences covering the most important recent developments. Lead with funding if applicable. Include specific numbers ($, headcount, growth %). Focus on signals indicating growing operational volume, scaling challenges, or manual workflow bottlenecks.]

**Team & hiring signals:** [Employee count if findable. Size of operations team if estimable. Key hires. Call out any operations, prior auth, rev cycle, data entry, or integration engineering hiring. Note contact's background and relevance to an automation buying decision.]

**Best pitch angle:** [3-5 sentences. Identify the PRIMARY use case for Asteroid. Connect to a specific business trigger. Quantify the opportunity using the benchmarks above. Reference the most relevant Asteroid customer proof point (Thyme Care, Vitable, Moonset, InTouchNow, Delfa). Explain why APIs don't solve this and why RPA breaks.]

**Personalization hooks:**
- [Specific thing #1 to reference in the email opener that proves real research]
- [Specific thing #2]
- [Specific thing #3]

**Primary use case:** [One of: Prior Auth Automation | Coverage Verification | Claims Status | EHR Data Entry (Browser) | EHR Data Entry (Citrix/CUA) | Fax Workflows | Voice-to-Browser Pipeline | Clinical Trial Enrollment | Portal Sync | Multi-use]

**Estimated deal size:** [Based on company size and use case: $3K-6K/mo for startups, $6K-15K/mo for mid-market, $10K-50K/mo for larger ops, $50K-200K+/mo for enterprise]

---STRUCTURED_DATA---
COMPANY_SIZE: [Employee range or "Not publicly available"]
PITCH_ANGLE: [One sentence summary of the single best pitch angle]
PRIMARY_USE_CASE: [Single use case label from the list above]
ESTIMATED_DEAL_SIZE: [Dollar range per month]
PRIORITY: [1-5]

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
1. Think in terms of portal work and browser tasks, not websites or design. Every insight must connect to: Does this company's ops team spend significant time manually logging into portals, filling forms, checking statuses, or entering data in browser-based systems?
2. Healthcare sub-vertical matters enormously. Prior auth companies, RCM firms, oncology navigation, direct primary care, specialty pharmacy, hospice/home health, clinical trial CROs, and dental/vision benefits administrators are Asteroid's sweet spots.
3. Legacy systems = opportunity. Companies working with older EHRs, Citrix environments, payer portals with no APIs, or government health systems are the strongest fits.
4. Hiring = strongest signal. Operations staff hiring, prior auth specialist hiring, coverage verification analyst hiring, data entry hiring directly indicate manual portal volume that Asteroid can automate.
5. Quantify the pain. "They do prior auths" is not enough. "They process ~500 prior auths daily across 20+ payer portals, each taking 20-30 minutes manually" is what closes deals.
6. Reference the right proof point. Match each prospect to the most relevant Asteroid customer: high-volume ops across portals = Thyme Care; multi-carrier coverage verification = Vitable Health; Citrix/legacy desktop EMRs = Moonset Health; voice AI + browser automation = InTouchNow or Delfa; clinical trials = Delfa.
7. Flag RPA frustration. If a company mentions UiPath, Automation Anywhere, or Blue Prism, they have tried automation and may be frustrated. Asteroid's self-healing agents and no-code builder are the upgrade pitch.
8. No fluff. Every sentence must contain information usable in an email or a go/no-go decision.
9. Be honest about weak fits. If a company operates entirely on modern API-first platforms, or their portal work volume is low, say so.
10. Compliance is a feature. Note if the prospect operates in high-compliance environments (HIPAA, state-specific regulations, payer audit requirements). Asteroid's full audit trail on every execution is a differentiator.

---

OUR COMPANY CONTEXT:
{RESEARCH_CONTEXT}"""


def research_company(company_name, website, contact_name="", contact_title="", industry="", description="", location=""):
    """
    Use Claude to research a healthcare prospect using the Asteroid.ai intelligence methodology.

    Args:
        company_name: Company name
        website: Company website
        contact_name: Contact person name (optional)
        contact_title: Contact person title (optional)
        industry: Company industry (optional)
        description: Company description (optional)
        location: Company location (optional)

    Returns:
        dict: Research data with structured fields
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    client = Anthropic(api_key=api_key)
    prompt = build_research_prompt(company_name, website, contact_name, contact_title, industry, description, location)

    print(f"Researching {company_name}...")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system="You are a senior B2B sales intelligence analyst specializing in healthcare operations and automation. Produce research for Asteroid.ai's sales team. Be specific, factual, and actionable. Every insight should connect to manual browser-based portal work that Asteroid's agents can automate. Think like someone who has been in healthcare operations trenches. Follow the output format exactly.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )

        research_text = response.content[0].text

        # Parse structured data block
        company_size = ""
        pitch_angle = ""
        primary_use_case = ""
        estimated_deal_size = ""
        priority = "3"

        if "---STRUCTURED_DATA---" in research_text:
            structured_section = research_text.split("---STRUCTURED_DATA---")[1]
            for line in structured_section.strip().split('\n'):
                line = line.strip()
                if line.startswith("COMPANY_SIZE:"):
                    val = line.replace("COMPANY_SIZE:", "").strip()
                    if val.lower() != "not publicly available":
                        company_size = val
                elif line.startswith("PITCH_ANGLE:"):
                    pitch_angle = line.replace("PITCH_ANGLE:", "").strip()
                elif line.startswith("PRIMARY_USE_CASE:"):
                    primary_use_case = line.replace("PRIMARY_USE_CASE:", "").strip()
                elif line.startswith("ESTIMATED_DEAL_SIZE:"):
                    estimated_deal_size = line.replace("ESTIMATED_DEAL_SIZE:", "").strip()
                elif line.startswith("PRIORITY:"):
                    raw = line.replace("PRIORITY:", "").strip()
                    nums = re.findall(r'(\d)', raw)
                    if nums:
                        priority = nums[0]

            research_text = research_text.split("---STRUCTURED_DATA---")[0].strip()

        # Extract personalization hooks
        hooks = []
        hooks_match = re.search(
            r'\*\*Personalization hooks:\*\*(.*?)(?:\*\*Primary use case|\*\*Estimated deal size|\Z)',
            research_text, re.DOTALL
        )
        if hooks_match:
            for line in hooks_match.group(1).strip().split('\n'):
                line = line.strip().lstrip('- ')
                if line:
                    hooks.append(line)

        # Extract operations profile
        ops_profile = ""
        ops_match = re.search(r'\*\*Operations profile:\*\*(.*?)(?=\n\*\*|\Z)', research_text, re.DOTALL)
        if ops_match:
            ops_profile = ops_match.group(1).strip()

        # Extract recent news
        recent_news = ""
        news_match = re.search(r'\*\*Recent news:\*\*(.*?)(?=\n\*\*|\Z)', research_text, re.DOTALL)
        if news_match:
            recent_news = news_match.group(1).strip()

        # Extract team & hiring signals
        team_info = ""
        team_match = re.search(r'\*\*Team & hiring signals:\*\*(.*?)(?=\n\*\*|\Z)', research_text, re.DOTALL)
        if team_match:
            team_info = team_match.group(1).strip()

        # Extract best pitch angle (full text)
        pitch_angle_full = ""
        pitch_match = re.search(r'\*\*Best pitch angle:\*\*(.*?)(?=\n\*\*|\Z)', research_text, re.DOTALL)
        if pitch_match:
            pitch_angle_full = pitch_match.group(1).strip()
        if not pitch_angle:
            pitch_angle = pitch_angle_full

        total_tokens = response.usage.input_tokens + response.usage.output_tokens

        research_data = {
            "company_name": company_name,
            "website": website,
            "research_text": research_text,
            "operations_profile": ops_profile,
            "recent_news": recent_news,
            "team_info": team_info,
            "pitch_angle": pitch_angle,
            "personalization_hooks": hooks,
            "primary_use_case": primary_use_case,
            "estimated_deal_size": estimated_deal_size,
            "company_size": company_size,
            "priority": priority,
            "researched_at": str(datetime.now()),
            "tokens_used": total_tokens
        }

        print(f"Research completed — Priority: {priority} stars | Use case: {primary_use_case} ({total_tokens} tokens)")

        return research_data

    except Exception as e:
        print(f"Research failed: {str(e)}")
        raise


def save_research(research_data, company_name):
    """Save research data to JSON file."""
    safe_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')

    filename = RESEARCH_DIR / f"{safe_name}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(research_data, f, indent=2, ensure_ascii=False)

    print(f"Research saved to: {filename}")
    return filename


def main():
    """CLI interface for single-company research."""
    import argparse

    parser = argparse.ArgumentParser(description="Research a healthcare prospect for Asteroid.ai outreach")
    parser.add_argument('--name', required=True, help="Company name")
    parser.add_argument('--website', required=True, help="Company website")
    parser.add_argument('--contact', default='', help="Contact person name")
    parser.add_argument('--title', default='', help="Contact person title")
    parser.add_argument('--industry', default='', help="Company industry")
    parser.add_argument('--description', default='', help="Company description")
    parser.add_argument('--location', default='', help="Company location")
    parser.add_argument('--save', action='store_true', help="Save research to file")
    parser.add_argument('--update-sheet', action='store_true', help="Update Google Sheet with research")

    args = parser.parse_args()

    try:
        research_data = research_company(
            args.name, args.website,
            contact_name=args.contact,
            contact_title=args.title,
            industry=args.industry,
            description=args.description,
            location=args.location
        )

        print("\n" + "=" * 80)
        print(f"RESEARCH: {args.name}")
        print("=" * 80)
        print(research_text := research_data['research_text'])
        print("=" * 80)
        print(f"Priority: {research_data['priority']} stars")
        print(f"Primary use case: {research_data['primary_use_case']}")
        print(f"Estimated deal size: {research_data['estimated_deal_size']}")

        if args.save:
            save_research(research_data, args.name)

        if args.update_sheet:
            sys.path.insert(0, str(PROJECT_ROOT / "tools"))
            from manage_google_sheet import update_research_data
            success = update_research_data(args.name, research_data)
            if success:
                print(f"Updated Google Sheet for {args.name}")
            else:
                print(f"Warning: Could not update Google Sheet for {args.name}")

        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
