# Study Note Agent

An automated, AI-powered agent designed to read your Gmail inbox, filter for key learning emails, extract the knowledge, generate structured revision notes via an LLM, and save them directly into your Apple Notes app.

## Features
- **Gmail Integration:** Fetches emails via the official Gmail API with flexible filtering.
- **Smart Semantic Parsing:** Utilizes `markdownify` to intelligently preserve links, bold text, and code blocks from HTML payloads before sending them to the LLM.
- **AI Note Generation & Proofreading:** Uses Gemini (`gemini-2.5-flash`) to summarize the email into a structured format, followed by a secondary proofreading pass for maximum accuracy.
- **Robust Resiliency:** Natively handles API rate limits and transient network errors on Gemini and Microsoft Graph with Exponential Backoff (`tenacity`).
- **Concurrent Processing:** Uses `ThreadPoolExecutor` to process multiple fetched emails simultaneously at warp speed.
- **Microsoft OneNote Sync:** Saves the final, beautifully formatted notes directly to your Microsoft OneNote account via Graph API, working completely cross-platform on Linux, macOS, and Windows.
- **Deduplication:** Never processes the same email twice.

---

## 🛠 Setup Guide

### 1. Prerequisites
- Python 3.14+
- A Microsoft / Azure Dev account
- An Gemini API Key
- A Google Cloud Platform (GCP) project

### 2. Environment Configuration
Create a `.env` file in the root directory:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
MS_CLIENT_ID=your_microsoft_client_id_here
```

### 3. Install Dependencies
```bash
uv sync
```

### 4. Gmail API Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable the **Gmail API** under "APIs & Services".
4. Go to **Credentials** -> Create Credentials -> **OAuth client ID** (Application type: Desktop App).
5. Download the JSON file and save it as `credentials.json` in the root of this project.
6. The *first time* you run the script, a browser window will open asking you to log in to your Google account and authorize the app. A `token.json` file will then be created automatically for future runs.

### 5. Microsoft OneNote Setup
1. Go to the [Microsoft Azure Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade).
2. Register a new application (Supported account types: "Accounts in any organizational directory and personal Microsoft accounts").
3. Under **Authentication**, add a **Mobile and desktop applications** platform with the redirect URI `http://localhost`.
4. Copy your **Application (client) ID**.
5. Add it to your `.env` file as `MS_CLIENT_ID`.
6. The *first time* you run the script, a second browser window will open asking you to log in to your Microsoft account. A `onenote_token.json` file will then be created automatically for future runs.

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
uv run main.py --limit 5
```

### Arguments:
- `--limit`: Maximum number of emails to process in one execution (default: `5`, or configurable via `MAX_EMAILS_PER_RUN` in `constants.py`).

---

## 📄 Example Output

If you receive a 500-word newsletter about "Understanding React Server Components", the agent will generate and save a OneNote Page that looks like this:

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
