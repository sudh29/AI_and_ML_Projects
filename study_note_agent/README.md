You are a senior Python engineer and AI systems architect.

I want you to build a production-ready AI agent in Python with the following requirements:

GOAL:
Create an automated agent that:
1. Reads my Gmail inbox
2. Filters and selects specific emails (based on subject, sender, or label)
3. Extracts the email content
4. Uses an LLM to:
   - Understand the topic
   - Generate structured notes
   - Make the notes suitable for both learning and revision
5. Saves the generated notes into the Apple Notes app

---

FUNCTIONAL REQUIREMENTS:

1. Gmail Integration:
   - Use Gmail API (OAuth2 authentication)
   - Read emails from inbox
   - Allow filtering by:
     - Subject keywords
     - Sender email
     - Labels
   - Fetch full email body (plain text or HTML → clean text)

2. Content Processing:
   - Extract meaningful text from email
   - Remove signatures, disclaimers, noise

3. AI Note Generation:
   - Use an LLM (OpenAI API)
   - Generate:
     - Summary
     - Key concepts
     - Bullet-point notes
     - Revision-friendly format
     - Optional: examples and explanations
   - Output format:
     - Title
     - Summary
     - Key Points
     - Detailed Notes
     - Quick Revision Section

4. Apple Notes Integration:
   - Save notes into Apple Notes
   - Use macOS automation (AppleScript or pyobjc)
   - Create a new note with:
     - Title = Email subject
     - Body = Generated notes

5. Automation:
   - Modular design
   - Can run as:
     - Script
     - Scheduled job (cron)

---

TECHNICAL REQUIREMENTS:

- Language: Python
- Use clean architecture:
  - gmail_service.py
  - llm_service.py
  - notes_service.py
  - main.py

- Libraries:
  - google-api-python-client
  - google-auth
  - openai (or latest SDK)
  - beautifulsoup4 (for HTML parsing)

- Follow best practices:
  - Environment variables for secrets
  - Error handling
  - Logging
  - Reusable functions

---

OUTPUT EXPECTATIONS:

Provide:
1. Complete working Python code
2. Step-by-step setup guide:
   - Gmail API setup
   - OAuth credentials
   - Apple Notes automation setup
3. Example run
4. Sample output notes

---

BONUS (if possible):
- Add support for:
  - Multiple emails processing
  - Tagging notes
  - Deduplication (avoid reprocessing same email)
  - CLI interface

---

IMPORTANT:
- Keep code clean and production-ready
- Avoid unnecessary complexity
- Add comments for clarity
- Ensure it works on macOS (for Apple Notes integration)
