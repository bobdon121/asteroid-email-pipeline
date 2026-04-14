#!/usr/bin/env python3
"""One-time script to load 20 new prospects into Google Sheet."""
import sys, time, pickle
sys.path.insert(0, 'tools')
import gspread
from dotenv import load_dotenv
load_dotenv()

with open('token.pickle', 'rb') as f:
    creds = pickle.load(f)
gc = gspread.authorize(creds)
ws = gc.open_by_key('1OxXcnMmYmKZEalVF3SyhkYfS5fQFl_m_6nvHHRHKkW8').worksheet('Prospects')

prospects = [
    ('SmartStop Self Storage', 'smartstopselfstorage.com', 'jdolan@smartstop.com', 'Jamie Dolan', 'Real Estate',
     'Technology-driven REIT based in Ladera Ranch, California. One of the largest self-storage companies in North America, operating across the US and Canada. Listed on NYSE under SMA. Provides storage solutions for personal and business needs with online rentals, keypad access, 24-hour surveillance, and climate-controlled units. Post-IPO Debt CA$500M raised June 2025.'),
    ('Definely', 'definely.com', 'feargus@trydefinely.com', 'Feargus Macdaeid', 'Information Technology & Services',
     'LegalTech company simplifying creation, drafting, and review of legal documents. Founded by two former Magic Circle lawyers. Products include Vault, Draft, Enhance (AI drafting), Proof (proofreading), and PDF tool. Used by Dentons, Deloitte, and A&O Shearman. Backed by Microsoft. Series B $30M raised June 2025.'),
    ('Atome', 'atome.sg', '', 'Bernard Chan', 'Financial Services',
     'Southeast Asia leading buy now pay later (BNPL) provider founded 2019. Part of Atome Financial under Advance Intelligence Group. Uses AI-driven technology for flexible payment solutions. Operates in 9 markets across Southeast Asia and Greater China, partnering with 5,000+ retailers. Debt Financing $75M raised June 2025.'),
    ('Conveyor', 'conveyor.com', 'chas@conveyor.com', 'Chas Ballew', 'Information Technology & Services',
     'AI-powered software automating customer trust workflows for B2B businesses. Offers automated security questionnaire response tool, custom branded trust portals, and secure document sharing. Helps vendors generate answers to security questionnaires and RFPs. Series B $20M raised June 2025.'),
    ('Olyzon', 'olyzon.tv', 'martin@olyzon.tv', 'Martin Danet', 'Marketing & Advertising',
     'Paris-based adtech company specializing in programmatic advertising for connected TV (CTV) and video environments. Platform uses contextual targeting and AI-driven optimization. Enables privacy-compliant video campaigns optimized for measurable ROI. Seed $3.8M raised June 2025.'),
    ('Parallel Bio', 'parallel.bio', 'robert@parallel.bio', 'Robert Difazio', 'Biotechnology',
     'Biotechnology company improving drug development and immunology research through advanced human immune system modeling. Develops human-relevant experimental systems to predict immune responses more accurately than animal testing. Helps pharma companies evaluate vaccine and drug candidates earlier. Series A $21M raised June 2025.'),
    ('Wow Momo', 'wowmomo.com', 'mithun.appaiah@wowmomo.com', 'Mithun Appaiah', 'Food & Beverages',
     'Indian QSR chain founded 2008, headquartered in Kolkata. Specializes in momos with expansion into burgers, fried snacks, beverages, and desserts. Multiple sub-brands including Wow! China and Wow! Chicken. 600+ outlets across India. Debt Financing INR 850M raised June 2025.'),
    ('Nominal', 'nominal.io', 'cameron@nominal.io', 'Cameron McCord', 'Information Technology & Services',
     'Data infrastructure platform for mission-critical systems in aerospace, defense, and advanced manufacturing. Provides platforms for managing telemetry, test data, and operational analytics for complex hardware systems. Enables engineering teams to centralize, analyze, and collaborate on technical performance data in real time. Series B $75M raised June 2025.'),
    ('Iterate.ai', 'iterate.ai', 'brian@iterate.ai', 'Brian Sathianathan', 'Information Technology & Services',
     'Enterprise AI innovation platform helping companies rapidly prototype, validate, and deploy AI-powered applications. Low-code platform integrating with enterprise systems to accelerate AI experimentation. Enables enterprises to adopt generative AI and automation without heavy engineering overhead. Venture Round $15M raised June 2025.'),
    ('Zorro', 'myzorro.co', 'guy.e@myzorro.co', 'Guy Ezekiel', 'Insurance',
     'Insurance technology company simplifying personal insurance through digital-first experiences. Offers renters and personal property insurance designed to be simple, transparent, and easy to manage online. Leverages automation and modern underwriting models for flexible coverage options for urban renters. Series A $20M raised June 2025.'),
    ('Jomboy Media', 'jomboymedia.com', 'jimmy@jomboymedia.com', 'Jimmy OBrien', 'Media Production',
     'Digital media company focused on sports content, particularly baseball. Founded by Jimmy OBrien (Jomboy), gained popularity through viral sports commentary videos. Produces podcasts, YouTube content, merchandise, and sports commentary. Independent sports media brand partnering with athletes, expanding into multiple sports verticals. Series A $5M raised June 2025.'),
    ('Tastewise', 'tastewise.io', 'alon@tastewise.io', 'Alon Chen', 'Food Technology',
     'Food intelligence platform powered by AI helping food brands, retailers, and restaurants understand consumer trends in real time. Analyzes billions of data points from menus, recipes, and social conversations for predictive insights about emerging food trends. Series B $50M raised June 2025.'),
    ('Bolo AI', 'bolo.ai', 'varun@bolo.ai', 'Varun Mohan', 'Artificial Intelligence',
     'AI-powered copilots for industrial and enterprise environments. Improves operational efficiency by providing AI systems that answer technical questions, retrieve documentation, and automate knowledge workflows. Integrates with internal enterprise systems for instant access to structured and unstructured knowledge. Seed $4M raised June 2025.'),
    ('Tempest Therapeutics', 'tempesttx.com', 'swhiting@tempesttx.com', 'Sam Whiting', 'Biotechnology',
     'Clinical-stage biotechnology company developing targeted and immune-mediated therapies for cancer treatment. Advancing small molecule therapeutics to modulate tumor microenvironments and improve anti-tumor immune responses. Pipeline includes therapies for liver cancer and other solid tumors. Post-IPO Equity $30M raised June 2025.'),
    ('Ontra', 'ontra.ai', 'troy@ontra.ai', 'Troy Pospisil', 'Legal Technology',
     'Legal automation platform streamlining contract negotiation and management for private markets. AI-driven contract automation and workflow tools for investment firms and legal teams. Supports VC, private equity, and asset management firms in handling high volumes of legal agreements. Series B $70M raised June 2025.'),
    ('Coco', 'ridecoco.com', 'zach@ridecoco.com', 'Zach Rash', 'Robotics',
     'Robotics delivery company building small autonomous vehicles for last-mile food delivery. Partners with restaurants to provide sustainable and efficient urban delivery solutions. Robots operate on sidewalks and are remotely monitored for safety and reliability. Series A $36M raised June 2025.'),
    ('PostHog', 'posthog.com', 'james@posthog.com', 'James Hawkins', 'Developer Tools',
     'Open-source product analytics platform designed for developers. Offers tools for product analytics, feature flags, session replay, A/B testing, and data warehousing. Enables teams to analyze user behavior and iterate on products rapidly without multiple disconnected tools. Series C $50M raised June 2025.'),
    ('Sintra.ai', 'sintra.ai', 'alex@sintra.ai', 'Alex Kim', 'Artificial Intelligence',
     'AI startup building tools that automate business workflows using generative AI. Platform enables teams to create AI agents for repetitive business tasks across operations, marketing, and customer support. Focuses on making AI automation accessible for startups and SMBs. Seed $2M raised June 2025.'),
    ('Tracksuit', 'gotracksuit.com', 'connor@gotracksuit.com', 'Connor Archbold', 'Market Research',
     'Brand tracking platform helping companies measure and grow brand performance. Provides continuous brand awareness and perception metrics for modern growth teams. Aims to democratize brand data and make it actionable for startups and scale-ups. Series A $20M raised June 2025.'),
    ('InSoil', 'insoil.ai', 'andrey@insoil.ai', 'Andrey Zaytsev', 'AgTech',
     'Agricultural technology company leveraging AI and data science to optimize soil health and crop productivity. Provides farmers with predictive insights and soil analytics to improve yield outcomes while promoting sustainable practices. Integrates satellite imagery, field data, and AI models for data-driven farming decisions. Seed $5M raised June 2025.'),
]

existing = ws.get_all_records()
existing_emails = {r.get('Contact Email', '').lower() for r in existing}
existing_companies = {r.get('Company Name', '').lower() for r in existing}

added = 0
skipped = 0
for company_name, website, email, contact, industry, description in prospects:
    if email and email.lower() in existing_emails:
        print(f'SKIP (duplicate email): {company_name}')
        skipped += 1
        continue
    if company_name.lower() in existing_companies:
        print(f'SKIP (duplicate company): {company_name}')
        skipped += 1
        continue

    row = [
        company_name, website, email, contact, industry,
        '', '', '', '',
        '',
        '', '', '',
        'Pending',
        '',
        'No', '',
        'No', '', '',
        'No', '',
        '', '',
        '',
        description
    ]
    ws.append_row(row)
    print(f'ADDED: {company_name} -> {email or "(no email)"}')
    added += 1
    time.sleep(1.2)

print(f'\nDone. Added: {added}, Skipped: {skipped}')
