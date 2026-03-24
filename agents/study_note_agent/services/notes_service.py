import atexit
import html
import logging
from pathlib import Path
import threading

import bleach
import jinja2
import markdown
from msal import PublicClientApplication, SerializableTokenCache
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

import constants


class NotesService:
    def __init__(self, token_path: str | Path | None = None) -> None:
        self.logger = logging.getLogger(__name__)
        if token_path is None:
            token_path = constants.ONENOTE_TOKEN_PATH
        self.token_path = Path(token_path)

        self.client_id = constants.MS_CLIENT_ID
        self.authority = constants.MICROSOFTONLINE

        if not self.client_id:
            raise ValueError(
                "Missing MS_CLIENT_ID environment variable. "
                "Please add your Microsoft Application ID to your .env file: MS_CLIENT_ID=your_id_here. "
                "See README.md for instructions on registering an Azure AD application."
            )

        self.cache = SerializableTokenCache()
        if self.token_path.exists():
            self.cache.deserialize(self.token_path.read_text())

        # Serializes MSAL cache access, interactive browser login, and disk writes.
        self._cache_lock = threading.Lock()

        def save_cache():
            with self._cache_lock:
                if self.cache.has_state_changed:
                    data = self.cache.serialize()
                    if isinstance(data, str):
                        self.token_path.write_text(data)

        atexit.register(save_cache)

        self.app = PublicClientApplication(
            self.client_id, authority=self.authority, token_cache=self.cache
        )

    def _get_access_token(self) -> str:
        """Acquires (or refreshes) a valid access token from the MSAL cache."""
        with self._cache_lock:
            result = None
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(
                    constants.ONENOTE_SCOPES, account=accounts[0]
                )

            if not result:
                self.logger.info(
                    "No cached OneNote token found. Opening browser for Microsoft login..."
                )
                result = self.app.acquire_token_interactive(
                    scopes=constants.ONENOTE_SCOPES
                )

        if not result:
            raise Exception(
                "Failed to acquire Microsoft token: authentication returned empty result."
            )
        if "access_token" not in result:
            raise Exception(
                "Failed to authenticate with Microsoft: %s"
                % result.get("error_description", result)
            )
        return result["access_token"]

    def save_note(self, title: str, markdown_content: str) -> bool:
        """Saves generated notes to Microsoft OneNote via Graph API."""

        # Validate inputs
        if not title or not isinstance(title, str):
            self.logger.error("Invalid title: title must be a non-empty string.")
            return False

        if not markdown_content or not isinstance(markdown_content, str):
            self.logger.error(
                "Invalid content: markdown_content must be a non-empty string."
            )
            return False

        if len(markdown_content.strip()) == 0:
            self.logger.error(
                "Invalid content: markdown_content cannot be only whitespace."
            )
            return False

        if len(markdown_content) > 1_000_000:
            self.logger.error(
                "Invalid content: markdown_content exceeds 1MB limit (size: %d bytes).",
                len(markdown_content),
            )
            return False

        try:
            html_content = markdown.markdown(markdown_content)
        except Exception as e:
            self.logger.error(
                "Failed to convert markdown to HTML for title '%s': %s", title, e
            )
            return False

        allowed_tags = list(bleach.sanitizer.ALLOWED_TAGS) + [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "span",
            "br",
            "hr",
            "pre",
            "code",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "img",
            "blockquote",
            "del",
        ]
        allowed_attrs = bleach.sanitizer.ALLOWED_ATTRIBUTES.copy()
        allowed_attrs.update(
            {
                "*": ["class", "id"],
                "img": ["src", "alt", "title"],
                "a": ["href", "title", "rel"],
            }
        )

        html_content = bleach.clean(
            html_content, tags=allowed_tags, attributes=allowed_attrs, strip=True
        )

        safe_title = html.escape(title)

        # OneNote requires a strict HTML wrapper
        template = jinja2.Template(
            "<!DOCTYPE html>\n"
            "<html>\n"
            "  <head>\n"
            "    <title>{{ title }}</title>\n"
            "  </head>\n"
            "  <body>\n"
            "    {{ content }}\n"
            "  </body>\n"
            "</html>"
        )
        onenote_html = template.render(title=safe_title, content=html_content)

        # Acquire a fresh token on each save to avoid mid-run expiry
        access_token = self._get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/xhtml+xml",
        }

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
        )
        def _post():
            response = requests.post(
                constants.GRAPH_ENDPOINT,
                headers=headers,
                data=onenote_html.encode("utf-8"),
                timeout=constants.ONENOTE_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response

        try:
            response = _post()
            # Safely extract OneNote page URL with multiple fallbacks
            try:
                response_json = response.json()
                page_url = (
                    response_json.get("links", {})
                    .get("oneNoteWebUrl", {})
                    .get("href", "")
                )
            except ValueError as json_error:
                self.logger.debug("Response was not valid JSON: %s", json_error)
                page_url = ""
            except Exception as url_error:
                self.logger.debug(
                    "Could not extract OneNote URL from response: %s", url_error
                )
                page_url = ""

            if page_url:
                self.logger.info("Successfully saved '%s' to OneNote.", title)
            else:
                self.logger.info("Successfully saved '%s' to OneNote.", title)
            return True
        except requests.RequestException as req_error:
            self.logger.error(
                "Network error saving '%s' to OneNote: %s", title, req_error
            )
            return False
        except Exception as e:
            self.logger.error(
                "Failed to save '%s' to OneNote after retries: %s", title, e
            )
            return False
