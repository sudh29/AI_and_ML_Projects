# constants.py
import os
import json
import re


def _load_config(filepath="config/config.json"):
    default_config = {"target_emails": [], "max_emails_per_run": 5}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                content = f.read()
                # Flexibly strip JSON comments (//) so you can temporarily disable emails!
                content = re.sub(r"^\s*//.*$", "", content, flags=re.MULTILINE)
                # Strip trailing commas that become exposed when the last array item is commented out
                content = re.sub(r",\s*([\]}])", r"\1", content)
                return json.loads(content)
        except json.JSONDecodeError:
            pass
    return default_config


_config = _load_config()

# List of email addresses to monitor for extraction
TARGET_EMAILS = _config.get("target_emails", [])

# Maximum number of emails to process in one execution
MAX_EMAILS_PER_RUN = _config.get("max_emails_per_run", 5)

PROMPT_GENERATE_NOTES = """
You are an expert technical summarizer and educator. 
Your job is to read an email and extract the valuable information into structured, revision-friendly notes.
Ignore pleasantries, disclaimers, signatures, and logistical noise.

Format your response in Markdown using exactly this structure:
# [Email Subject]

## Summary
[2-3 sentence high-level overview]

## Key Concepts
* [Concept 1]: [Brief explanation]
* [Concept 2]: [Brief explanation]

## Detailed Notes
[Organized bullet points containing the core information, examples, and technical details]

## Quick Revision
[3-4 rapid-fire Q&A style points or a TL;DR for quick memory recall]
"""

PROMPT_PROOFREAD_NOTES = """
You are an expert technical reviewer.
Your job is to read the original email content and the generated structured notes, 
and proofread the notes to ensure they are 100% accurate, capture all key details, 
and do not contain any hallucinations.

Fix any inaccuracies, grammatical errors, or missing critical details. 
Return ONLY the finalized, corrected Markdown notes in the exact same format.
"""
