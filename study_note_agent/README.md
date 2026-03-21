# Study Note Agent

An automated, AI-powered agent designed to read your Gmail inbox, filter for key learning emails, extract the knowledge, generate structured revision notes via an LLM, and save them directly into your Apple Notes app.

## Features
- **Gmail Integration:** Fetches emails via the official Gmail API with flexible filtering.
- **Content Cleaning:** Automatically parses plain text and deep HTML payloads, stripping noise.
- **AI Note Generation & Proofreading:** Uses OpenAI (`gpt-4o`) to summarize the email into a structured, revision-friendly format, followed by a secondary proofreading pass for maximum accuracy.
- **Apple Notes Sync:** Saves the final, beautifully formatted Notes directly onto your macOS machine using native AppleScript automation.
- **Deduplication:** Never processes the same email twice.

---

## 🛠 Setup Guide

### 1. Prerequisites
- Python 3.12+
- macOS (required for Apple Notes integration)
- An OpenAI API Key
- A Google Cloud Platform (GCP) project

### 2. Environment Configuration
Create a `.env` file in the root directory:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Install Dependencies
```bash
uv pip install -e .
```

### 4. Gmail API Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable the **Gmail API** under "APIs & Services".
4. Go to **Credentials** -> Create Credentials -> **OAuth client ID** (Application type: Desktop App).
5. Download the JSON file and save it as `credentials.json` in the root of this project.
6. The *first time* you run the script, a browser window will open asking you to log in to your Google account and authorize the app. A `token.json` file will then be created automatically for future runs.

---

## 🚀 Usage

Configuration of target emails to process natively lives in `constants.py`. Edit the `TARGET_EMAILS` list:

```python
TARGET_EMAILS = [
    "newsletter@tech.com",
    "learning@source.com"
]
```

Run the agent via the terminal:

```bash
python main.py --limit 5
```

### Arguments:
- `--limit`: Maximum number of emails to process in one execution (default: `5`, or configurable via `MAX_EMAILS_PER_RUN` in `constants.py`).

---

## 📄 Example Output

If you receive a 500-word newsletter about "Understanding React Server Components", the agent will generate and save an Apple Note that looks like this:

```markdown
# React Server Components Deep Dive

## Summary
The email provides an architectural overview of React Server Components (RSC), explaining how they shift rendering to the server to reduce client bundle sizes and improve performance latency.

## Key Concepts
* **Server-side Rendering (SSR):** Generating static HTML on the server before sending it down.
* **Hydration:** The process of attaching event listeners to static HTML on the client.

## Detailed Notes
* RSCs exclusively render on the server and do not ship JavaScript to the client.
* They are imported like standard components but cannot use context or hooks like `useState`.
* Best used for heavy dependencies like markdown parsers or direct database fetches.

## Quick Revision
* Q: Can you use `useEffect` in an RSC? 
  * A: No, they only run on the server.
* Q: How do RSCs affect bundle size?
  * A: They reduce bundle size by keeping heavy dependencies on the server.

---
*Tags: #ai-agent #email-notes*
```
