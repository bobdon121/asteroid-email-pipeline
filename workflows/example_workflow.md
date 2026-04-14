# Example Workflow Template

## Objective
[Clear, one-sentence description of what this workflow accomplishes]

## Required Inputs
- **Input 1**: [Description and format]
- **Input 2**: [Description and format]
- **Input 3**: [Optional - Description and format]

## Tools Required
- `tools/example_tool.py` - [What this tool does]
- `tools/another_tool.py` - [What this tool does]

## Workflow Steps

### 1. [Step Name]
**Action**: [What to do]
**Tool**: `tools/example_tool.py`
**Expected Output**: [What you should get]

```bash
python tools/example_tool.py --input "value"
```

### 2. [Step Name]
**Action**: [What to do]
**Tool**: `tools/another_tool.py`
**Expected Output**: [What you should get]

```bash
python tools/another_tool.py --data .tmp/intermediate_file.json
```

### 3. [Step Name]
**Action**: [What to do]
**Expected Output**: [What you should get]

## Expected Outputs
- **Primary Output**: [Where the final result goes - e.g., Google Sheet URL]
- **Intermediate Files**: `.tmp/intermediate_file.json` (temporary, can be regenerated)

## Edge Cases & Error Handling

### Rate Limits
- [How to handle if API rate limits are hit]
- [Recommended delays or batch sizes]

### Missing Data
- [What to do if required data is missing]
- [How to validate inputs before processing]

### API Failures
- [Retry strategy]
- [Fallback options]

## Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## Notes & Learnings
[Document any quirks, timing issues, or insights discovered while running this workflow]

---

**Last Updated**: [Date]
**Tested**: [Yes/No]
