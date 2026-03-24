"""Core agent workflow: fetch emails, generate notes, save, and reconcile."""

from __future__ import annotations

import concurrent.futures
import logging
import sqlite3
import sys

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

import constants
from email_types import FetchedEmail
from services.gmail_service import GmailService
from services.llm_service import LLMService
from services.notes_service import NotesService
from services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Circuit breaker
# ------------------------------------------------------------------
class CircuitBreaker:
    """Stop processing after too many consecutive API failures."""

    def __init__(self, failure_threshold: int = 5) -> None:
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.is_open = False

    def record_success(self) -> None:
        """Reset failure count on success."""
        self.failure_count = 0

    def record_failure(self) -> None:
        """Increment failure count and open circuit if threshold exceeded."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.error(
                "Circuit breaker opened: %d consecutive failures.",
                self.failure_count,
            )


# ------------------------------------------------------------------
# Deduplication helpers
# ------------------------------------------------------------------
def _init_db() -> None:
    constants.PROCESSED_EMAILS_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(constants.PROCESSED_EMAILS_DB, timeout=20.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def load_processed_emails() -> set[str]:
    """Load the set of already-processed email IDs from SQLite storage."""
    _init_db()
    with sqlite3.connect(constants.PROCESSED_EMAILS_DB, timeout=20.0) as conn:
        cursor = conn.execute("SELECT email_id FROM processed_emails")
        return {row[0] for row in cursor.fetchall()}


def save_processed_emails(new_ids: list[str] | set[str]) -> None:
    """Save a set/list of processed email IDs to SQLite storage."""
    if not new_ids:
        return
    try:
        with sqlite3.connect(constants.PROCESSED_EMAILS_DB, timeout=20.0) as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO processed_emails (email_id) VALUES (?)",
                [(email_id,) for email_id in new_ids],
            )
    except Exception as e:
        logger.error("Failed to save processed emails to DB: %s", e)


# ------------------------------------------------------------------
# Single-email pipeline
# ------------------------------------------------------------------
def process_email(
    email: FetchedEmail,
    llm: LLMService,
    notes: NotesService,
    whatsapp: WhatsAppService | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> str | None:
    """Process one email: generate notes, proofread, save.

    Returns the email ID on success so the caller can mark it
    as read from the main thread (Google API clients are not
    thread-safe).
    """
    if circuit_breaker and circuit_breaker.is_open:
        logger.warning("Circuit breaker is open. Skipping '%s'.", email["subject"])
        return None

    logger.info("Processing email: '%s'", email["subject"])

    logger.debug("Generating markdown notes via Gemini...")
    generated_notes = llm.generate_notes(email["subject"], email["content"])
    if not generated_notes:
        logger.error(
            "Failed to generate notes for '%s'. Skipping.",
            email["subject"],
        )
        return None

    logger.debug("Proofreading generated notes via Gemini...")
    proofread_notes = llm.proofread_notes(email["content"], generated_notes)
    if not proofread_notes:
        logger.warning(
            "Proofread failed for '%s'. Using raw version.",
            email["subject"],
        )
        proofread_notes = generated_notes

    final_output = f"{proofread_notes}\n\n---\n*Tags: #ai-agent #email-notes*"

    # Save to Microsoft OneNote
    success = notes.save_note(email["subject"], final_output)

    if success:
        if whatsapp is not None:
            preview = (
                proofread_notes[:500]
                if len(proofread_notes) <= 500
                else proofread_notes[:499] + "…"
            )
            if not whatsapp.notify_note_saved(email["subject"], preview=preview):
                logger.warning(
                    "WhatsApp notification failed for '%s' (OneNote save succeeded).",
                    email["subject"],
                )
        logger.debug(
            "Successfully processed and saved email '%s'.",
            email["subject"],
        )
        return email["id"]

    logger.error(
        "Failed to save notes for '%s' to OneNote.",
        email["subject"],
    )
    return None


# ------------------------------------------------------------------
# Main workflow
# ------------------------------------------------------------------
def run(
    *,
    limit: int = constants.MAX_EMAILS_PER_RUN,
    enable_whatsapp: bool = False,
) -> None:
    """Execute the full agent workflow.

    1. Build Gmail search query from config.
    2. Fetch and deduplicate emails.
    3. Process emails concurrently (LLM + OneNote + optionally WhatsApp).
    4. Mark processed emails as read and persist state.
    """
    # Load previously processed email IDs
    processed_emails = load_processed_emails()
    logger.info(
        "Loaded %d previously processed email IDs.",
        len(processed_emails),
    )

    # Build query from constants
    if constants.TARGET_EMAILS:
        senders_query = " OR ".join(
            [f"from:{email}" for email in constants.TARGET_EMAILS]
        )
        search_query = f"is:unread AND ({senders_query})"
    else:
        search_query = "is:unread label:learning"

    logger.info("Starting agent with query: '%s'", search_query)

    # Fetch emails
    gmail = GmailService()
    emails = gmail.fetch_emails(query=search_query)

    if not emails:
        logger.info("No unread emails matched the query. Nothing to do.")
        return

    # Filter out already-processed emails
    new_emails = [e for e in emails if e["id"] not in processed_emails]
    if not new_emails:
        logger.info(
            "All %d fetched emails already processed. Nothing to do.",
            len(emails),
        )
        return

    logger.info(
        "Found %d new unread emails (filtered from %d total).",
        len(new_emails),
        len(emails),
    )

    # Initialize services only when needed
    llm = LLMService()
    notes = NotesService()
    whatsapp: WhatsAppService | None = None
    if enable_whatsapp:
        whatsapp = WhatsAppService()
        logger.info("WhatsApp notifications enabled.")
    else:
        logger.info("WhatsApp notifications disabled (use --whatsapp to enable).")
    logger.info("All services initialized successfully.")

    emails_to_process = new_emails[:limit]

    # ---- concurrent processing ----
    circuit_breaker = CircuitBreaker(failure_threshold=5)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=constants.MAX_WORKERS_POOL
    ) as executor:
        futures = [
            executor.submit(process_email, email, llm, notes, whatsapp, circuit_breaker)
            for email in emails_to_process
        ]

        results: list[str | None] = []
        for f in concurrent.futures.as_completed(futures):
            try:
                result = f.result()
                if result:
                    circuit_breaker.record_success()
                else:
                    circuit_breaker.record_failure()
                results.append(result)
            except Exception as e:
                logger.error("Exception in email processing thread: %s", e)
                circuit_breaker.record_failure()
                results.append(None)

    # ---- mark as read from main thread ----
    successful_ids = [mid for mid in results if mid]
    mark_as_read_failures: list[str] = []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def retry_mark_as_read(msg_id: str) -> bool:
        success = gmail.mark_as_read(msg_id)
        if not success:
            raise RuntimeError(f"mark_as_read returned False for {msg_id}")
        return success

    for msg_id in successful_ids:
        try:
            retry_mark_as_read(msg_id)
        except Exception as e:
            mark_as_read_failures.append(msg_id)
            logger.warning(
                "Error marking email %s as read: %s. It may be reprocessed next run.",
                msg_id,
                e,
            )

    # ---- persist state ----
    processed_emails.update(successful_ids)
    save_processed_emails(successful_ids)

    if mark_as_read_failures:
        logger.warning(
            "Job complete. Processed %d emails, but failed to mark %d as read.",
            len(successful_ids),
            len(mark_as_read_failures),
        )
    else:
        logger.info(
            "Job complete. Successfully processed %d new emails.",
            len(successful_ids),
        )

    if circuit_breaker.is_open:
        marked_ok = len(successful_ids) - len(mark_as_read_failures)
        logger.critical(
            "Circuit breaker tripped. "
            "%d save(s) written to dedup storage. "
            "Gmail mark-as-read: %d ok, %d failed.",
            len(successful_ids),
            marked_ok,
            len(mark_as_read_failures),
        )
        sys.exit(1)
