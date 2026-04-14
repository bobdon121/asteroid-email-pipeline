# Email Template Guide

## How Templates Work

1. You write the **structure and instructions** in a template file
2. ChatGPT researches the company (industry, founder, pain points, etc.)
3. Claude AI reads your template + the research and writes a personalized email
4. Each email is unique - tailored to the specific company

## Template Format

Every template needs a YAML header and instruction blocks:

```markdown
---
name: Template Name
tone: professional, helpful
max_length: 150 words
---

Subject: [Instructions for AI to create the subject line]

Hi {contact_name},

[Instruction block: What this paragraph should contain]

[Instruction block: What this paragraph should contain]

Best,
{sender_name}
{sender_title}
{sender_company}
```

## Available Placeholders

These get replaced automatically:
- `{contact_name}` - Recipient's name
- `{company_name}` - Company name
- `{sender_name}` - Your name (from .env)
- `{sender_title}` - Your title (from .env)
- `{sender_company}` - Your company (from .env)

## Writing Effective Cold Emails

### DO:
- Keep emails under 150 words
- Reference specific company research
- Focus on THEIR problems, not your features
- Use one clear call-to-action
- Write like a human, not a marketing bot
- Use the founder/CEO name if relevant

### DON'T:
- Use "Free", "Guarantee", or spam trigger words
- Write walls of text
- Use multiple CTAs
- Be vague or generic
- Use excessive formatting, caps, or exclamation marks

## Adding New Templates

1. Create a new file: `templates/template4.md`
2. Follow the format above
3. The system will automatically include it in the rotation
4. Track performance in the Google Sheet "Templates" tab
