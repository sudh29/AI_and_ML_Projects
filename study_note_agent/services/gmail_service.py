import base64
import logging
from pathlib import Path
import httplib2
import markdownify
import constants
from email_types import FetchedEmail
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GmailService:
    def __init__(
        self,
        credentials_path=None,
        token_path=None,
    ):
        if credentials_path is None:
            credentials_path = _PROJECT_ROOT / "config" / "credentials.json"
        if token_path is None:
            token_path = _PROJECT_ROOT / "config" / "token.json"
        credentials_path = Path(credentials_path)
        token_path = Path(token_path)
        self.creds = None
        self.token_path = token_path

        if token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_file(
                    str(token_path), SCOPES
                )
                logger.debug("Loaded cached credentials from %s", token_path)
            except Exception as e:
                logger.warning("Failed to load cached token from %s: %s", token_path, e)
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    logger.debug("Successfully refreshed cached credentials.")
                except Exception as e:
                    logger.warning(
                        "Failed to refresh credentials: %s. Will re-authenticate.", e
                    )
                    self.creds = None

            if not self.creds:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {credentials_path}. "
                        "Please download your Google OAuth credentials from the Google Cloud Console "
                        "and save them as 'config/credentials.json'. "
                        "See README.md for setup instructions."
                    )
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path), SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                    logger.info("Successfully authenticated with Gmail API.")
                except Exception as e:
                    raise Exception(
                        f"Failed to authenticate with Gmail API: {e}. "
                        "Ensure credentials.json is valid and contains the correct OAuth client ID."
                    )

            token_path.write_text(self.creds.to_json())

        authorized_http = AuthorizedHttp(
            self.creds,
            http=httplib2.Http(timeout=constants.GMAIL_REQUEST_TIMEOUT),
        )
        self.service = build("gmail", "v1", http=authorized_http, cache_discovery=False)

    def fetch_emails(self, query: str = "is:unread") -> list[FetchedEmail]:
        """Fetches emails matching the Gmail search query."""
        messages: list[dict] = []
        page_token = None
        pages = 0
        try:
            while pages < constants.GMAIL_LIST_MAX_PAGES:
                results = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=query,
                        maxResults=constants.GMAIL_LIST_MAX_RESULTS,
                        pageToken=page_token,
                    )
                    .execute()
                )
                batch = results.get("messages", [])
                messages.extend(batch)
                page_token = results.get("nextPageToken")
                pages += 1
                if not page_token:
                    break
            if page_token:
                logger.warning(
                    "Gmail messages.list stopped after %d page(s); more results exist.",
                    pages,
                )
        except HttpError as e:
            logger.error("HTTP Error fetching email list: %s", e)
            return []

        logger.debug(
            "Found %d messages matching query (%d list page(s)).", len(messages), pages
        )

        email_data = []
        for msg in messages:
            try:
                msg_id = msg["id"]
                message = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )

                headers = message["payload"].get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"].lower() == "subject"),
                    "No Subject",
                )
                sender = next(
                    (h["value"] for h in headers if h["name"].lower() == "from"),
                    "Unknown Sender",
                )

                body = self._extract_body(message["payload"])
                clean_text = self._clean_html(body)

                email_data.append(
                    {
                        "id": msg_id,
                        "subject": subject,
                        "sender": sender,
                        "content": clean_text,
                    }
                )
                logger.debug(
                    "Successfully parsed email from '%s': '%s'", sender, subject
                )
            except Exception as e:
                logger.error(
                    "Error processing email %s: %s", msg.get("id", "Unknown"), e
                )
                continue

        logger.info(
            "Successfully fetched and parsed %d emails (failed: %d).",
            len(email_data),
            len(messages) - len(email_data),
        )
        return email_data

    def _extract_body(self, payload: dict) -> str:
        """Recursively extracts the best available body text from the payload parts.

        Prefers text/html over text/plain so that markdownify can preserve
        rich formatting (links, bold, code blocks, tables).
        """
        if "parts" in payload:
            # First pass: look for HTML
            for part in payload["parts"]:
                if part["mimeType"] == "text/html" and "data" in part["body"]:
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                elif part["mimeType"].startswith("multipart/"):
                    body = self._extract_body(part)
                    if body:
                        return body
            # Second pass: fall back to plain text
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
        elif "body" in payload and "data" in payload["body"]:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        return ""

    def mark_as_read(self, msg_id: str) -> bool:
        """Removes the UNREAD label from the specified email."""
        try:
            self.service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except HttpError as e:
            logger.error("HTTP Error marking email %s as read: %s", msg_id, e)
            return False

    def _clean_html(self, html_content: str) -> str:
        """Converts HTML structurally into Markdown to preserve semantics for the LLM."""
        # markdownify smartly drops script/style tags and perfectly retains hyperlinks,
        # bold, table layouts, and list elements natively in Markdown output.
        clean_markdown = markdownify.markdownify(html_content, heading_style="ATX")
        return clean_markdown.strip()
