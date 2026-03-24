from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import markdownify
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from services.llm_service import LLMService
    from services.notes_service import NotesService
    from services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 20
_MAX_CONTENT_LENGTH = 500_000  # ~500 KB of text


class WebService:
    """Extracts text from web pages and feeds them through the note pipeline."""

    @staticmethod
    def _derive_title(url: str) -> str:
        """Build a human-readable title from a URL."""
        parsed = urlparse(url)
        # Use the domain + path, stripping trailing slashes
        path = parsed.path.rstrip("/")
        if path and path != "/":
            return f"Web: {parsed.netloc}{path}"
        return f"Web: {parsed.netloc}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    def _fetch_html(self, url: str) -> str:
        """Download the raw HTML of a page with retries."""
        response = requests.get(
            url,
            timeout=_REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; StudyNoteAgent/1.0; "
                    "+https://github.com/sudh29/AI_and_ML_Projects)"
                ),
            },
        )
        response.raise_for_status()
        return response.text

    def extract_text(self, url: str) -> str:
        """Fetch a web page and convert its HTML to clean markdown text.

        Args:
            url: The full URL of the web page.

        Returns:
            The extracted text content as markdown.

        Raises:
            Exception: If the page cannot be fetched or parsed.
        """
        try:
            html = self._fetch_html(url)
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch '{url}': {e}")

        # Convert HTML → markdown (strips tags, keeps structure)
        text = markdownify.markdownify(
            html,
            strip=["img", "script", "style", "nav", "footer", "header"],
        )

        # Clean up excessive whitespace
        lines = [line.rstrip() for line in text.splitlines()]
        text = "\n".join(lines).strip()

        if not text:
            raise Exception(f"No text content extracted from '{url}'.")

        # Truncate very large pages to stay within LLM context limits
        if len(text) > _MAX_CONTENT_LENGTH:
            logger.warning(
                "Content from '%s' truncated from %d to %d chars.",
                url,
                len(text),
                _MAX_CONTENT_LENGTH,
            )
            text = text[:_MAX_CONTENT_LENGTH]

        return text

    def process_page(
        self,
        url: str,
        llm: LLMService,
        notes: NotesService,
        whatsapp: WhatsAppService | None = None,
    ) -> bool:
        """Full pipeline: extract text → LLM notes → proofread → save to OneNote.

        Args:
            url: The web page URL to process.
            llm: An initialised ``LLMService`` instance.
            notes: An initialised ``NotesService`` instance.
            whatsapp: Optional ``WhatsAppService`` instance for notifications.

        Returns:
            ``True`` if notes were generated and saved successfully.
        """
        title = self._derive_title(url)
        logger.info("Processing web page: %s", url)

        # 1. Extract text from the page
        try:
            content = self.extract_text(url)
        except Exception as e:
            logger.error("Text extraction failed for '%s': %s", url, e)
            return False

        logger.info("Extracted text from '%s' (%d chars).", url, len(content))

        # 2. Generate structured notes via LLM
        generated_notes = llm.generate_notes(title, content)
        if not generated_notes:
            logger.error("Failed to generate notes for '%s'. Skipping.", title)
            return False

        # 3. Proofread notes
        proofread_notes = llm.proofread_notes(content, generated_notes)
        if not proofread_notes:
            logger.warning("Proofread failed for '%s'. Using raw version.", title)
            proofread_notes = generated_notes

        final_output = (
            f"{proofread_notes}\n\n---\n*Source: {url}*\n*Tags: #ai-agent #web-notes*"
        )

        # 4. Save to OneNote
        success = notes.save_note(title, final_output)

        if success:
            logger.info("Successfully saved notes for '%s' to OneNote.", title)
            if whatsapp is not None:
                preview = (
                    proofread_notes[:500]
                    if len(proofread_notes) <= 500
                    else proofread_notes[:499] + "…"
                )
                if not whatsapp.notify_note_saved(title, preview=preview):
                    logger.warning("WhatsApp notification failed for '%s'.", title)
        else:
            logger.error("Failed to save notes for '%s' to OneNote.", title)

        return success
