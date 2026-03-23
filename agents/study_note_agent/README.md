# Study Note Agent

An automated, AI-powered agent designed to read your Gmail inbox, filter for key learning emails, extract the knowledge, generate structured revision notes via an LLM, and save them directly into your Microsoft OneNote.

## Features
- **Gmail Integration:** Fetches emails via the official Gmail API with flexible filtering.
- **Smart Semantic Parsing:** Utilizes `markdownify` to intelligently preserve links, bold text, and code blocks from HTML payloads before sending them to the LLM.
- **AI Note Generation & Proofreading:** Uses Gemini (`gemini-2.5-flash`) to summarize the email into a structured format, followed by a secondary proofreading pass for maximum accuracy.
- **Robust Resiliency:** Natively handles API rate limits and transient network errors on Gemini and Microsoft Graph with Exponential Backoff (`tenacity`).
- **Concurrent Processing:** Uses `ThreadPoolExecutor` to process multiple fetched emails simultaneously at warp speed.
- **Microsoft OneNote Sync:** Saves the final, beautifully formatted notes directly to your Microsoft OneNote account via Graph API, working completely cross-platform on Linux, macOS, and Windows.
- **WhatsApp (optional):** After a successful OneNote save, sends you a short [CallMeBot](https://www.callmebot.com/blog/free-api-whatsapp-messages/) WhatsApp message with the email subject and a text preview. **Privacy:** that content is sent to CallMeBot’s infrastructure; disable WhatsApp if that is not acceptable.
- **Deduplication:** Never processes the same email twice.
- **Circuit Breaker:** Automatically stops processing after 5 consecutive API failures to prevent cascading errors.
- **Thread-Safe:** Handles exceptions in worker threads gracefully without crashing the entire job.

---

## ⚙️ Architecture & Limitations

### Timeout Management
Request timeouts (seconds) are defined in `constants.py` and applied as follows:
- **OneNote API:** 15 seconds (`requests` timeout on Graph POST)
- **Gemini API:** 30 seconds (`google.genai` `HttpOptions.timeout` in milliseconds)
- **Gmail API:** 30 seconds (`httplib2.Http` passed to `AuthorizedHttp` for the API client)

If you still see hangs, use a process supervisor (e.g. `systemd`, Docker) with a wall-clock limit.

### Circuit Breaker Behavior
If the agent encounters 5 consecutive completed-task failures (ordering follows `as_completed`, not submission order), the circuit breaker opens. In-flight work in the thread pool is **not** cancelled: the pool waits for every submitted email to finish. After that:

1. IDs for successful OneNote saves are merged into deduplication storage; the agent attempts to mark each of those messages as read in Gmail (with retries). If the breaker tripped, the critical log states how many mark-as-read attempts succeeded vs failed.
2. A critical log line records that the circuit breaker tripped.
3. The process exits with status code **1** so schedulers (cron, systemd) can treat the run as failed.

This limits wasted API quota on repeated failures while preserving successful work.

### Thread Safety
- Email fetching and marking as read are single-threaded (Gmail API requires this)
- Email processing runs in parallel; Gemini calls are serialized with a lock because `google.genai` clients are not assumed thread-safe
- OneNote saves run in parallel; token acquisition uses a single lock so interactive Microsoft login cannot run from multiple threads at once
- Deduplication file updates happen on the main thread after workers finish

---

## 🛠 Setup Guide

### 1. Prerequisites
- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (installs dependencies and can manage the virtual environment)
- A Microsoft / Azure Dev account
- A Gemini API Key
- A Google Cloud Platform (GCP) project

### 2. Project setup (virtualenv + dependencies)

From the `study_note_agent` directory:

```bash
uv venv --python 3.14
```

Create and use the environment (Linux / macOS):

**Bash / Zsh:**

```bash
source .venv/bin/activate
```

**Fish** (do not use the bash `activate` script in Fish):

```fish
source .venv/bin/activate.fish
```

On Windows (cmd):

```bash
.venv\Scripts\activate.bat
```

On Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

Install packages from the lockfile (runtime + dev tools such as Ruff and pytest):

```bash
uv sync --group dev
```

You can skip manual activation and run commands through uv, for example:

```bash
uv run python main.py --limit 3
```

**Pre-commit (optional):** This repo’s Git root is the parent `AI_and_ML_Projects` folder. Ruff/Black in the root config are limited to `study_note_agent/`. To use only this project’s hook file:

```bash
# from AI_and_ML_Projects (repository root)
uv run pre-commit run --all-files --config study_note_agent/.pre-commit-config.yaml
uv run pre-commit install --config study_note_agent/.pre-commit-config.yaml
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
MS_CLIENT_ID=your_microsoft_client_id_here
# Optional: WhatsApp ping via CallMeBot after each OneNote save (see whatsapp_service.py)
CALLMEBOT_API_KEY=your_apikey_from_the_bot
CALLMEBOT_PHONE=+34123456789
```
Activate CallMeBot on your phone per [their guide](https://www.callmebot.com/blog/free-api-whatsapp-messages/) (personal-use API; omit these vars to disable notifications). Prefer putting API keys in `.env` rather than `config.json` so they are less likely to be committed by mistake.

### 4. Gmail API Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable the **Gmail API** under "APIs & Services".
4. Go to **Credentials** -> Create Credentials -> **OAuth client ID** (Application type: Desktop App).
5. Download the JSON file and save it as `config/credentials.json` in this project.
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

Configuration of target emails lives in `config/config.json`. Edit the `target_emails` list:

```json
{
  "target_emails": [
    "newsletter@tech.com",
    "learning@source.com"
  ],
  "max_emails_per_run": 5
}
```

Run the agent via the terminal:

```bash
uv run main.py --limit 5
uv run main.py --whatsapp

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

---

## 🔧 Configuration

### config/config.json
Customize the agent behavior:
```json
{
  "target_emails": [
    "sender1@example.com",
    "sender2@example.com"
  ],
  "max_emails_per_run": 5,
  "gemini_model": "gemini-2.5-flash"
}
```

- **target_emails:** List of email addresses to monitor (use `//` to comment out)
- **max_emails_per_run:** Maximum emails to process in a single execution
- **gemini_model:** Which Gemini model to use for note generation (configurable for cost/quality tradeoffs)

### Concurrency Settings
Edit `constants.py` to adjust:
- `MAX_WORKERS_POOL = 5` - Number of concurrent email processing threads
- `MAX_EMAILS_PER_RUN = 5` - Default limit per run

---

## 🐛 Troubleshooting

### "Circuit breaker opened: 5 consecutive API failures"
The agent detected repeated API failures and stopped processing to prevent cascading errors.

**Solutions:**
1. Check internet connectivity
2. Verify API credentials (GEMINI_API_KEY, MS_CLIENT_ID)
3. Check API quota and rate limits in respective dashboards
4. Wait a few minutes and retry (may be temporary outage)
5. Review logs in `console` for specific error messages

### "Failed to mark email as read"
The note was saved but the email couldn't be marked as read. It will be reprocessed next run.

**Solutions:**
1. This is non-critical (deduplication handles it)
2. May indicate rate limiting on Gmail API
3. Check Gmail OAuth token is still valid

### Agent times out or hangs
The agent may hang indefinitely if API requests aren't completing.

**Solutions:**
1. Run with a process timeout:
   ```bash
   timeout 300 uv run main.py --limit 5
   ```
2. Check network connectivity and firewall settings
3. Verify API endpoints are reachable
4. Review logs for the last processed email

### Thread exceptions crash the job
Previously critical, but now handled gracefully with the circuit breaker.

**Current behavior:**
- Individual thread exceptions are caught and logged
- Exception counts toward the circuit breaker threshold
- Job continues until 5 exceptions or all emails processed

---

## 📊 Performance Tips

1. **Run during off-peak hours:** Avoid rate limits by running when APIs have lower load
2. **Adjust concurrency:** Lower `MAX_WORKERS_POOL` if hitting rate limits, increase for faster processing
3. **Batch processing:** Use `--limit` flag to process fewer emails per run: `uv run main.py --limit 3`
4. **Use skill files:** Custom skill files in `skills/` directory enable specialized summarization

---

## 📝 License

[Add your license here]
