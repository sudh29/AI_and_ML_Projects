import argparse
import logging
from logging_config import setup_logging
from dotenv import load_dotenv
from services.gmail_service import GmailService
from services.llm_service import LLMService
from services.notes_service import NotesService
import constants

setup_logging()

logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="AI Agent to turn Emails into Apple Notes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=constants.MAX_EMAILS_PER_RUN,
        help="Maximum number of emails to process in one run",
    )
    args = parser.parse_args()

    # Build query from constants file target emails
    if constants.TARGET_EMAILS:
        senders_query = " OR ".join(
            [f"from:{email}" for email in constants.TARGET_EMAILS]
        )
        # Only fetch emails that are still unread
        search_query = f"is:unread AND ({senders_query})"
    else:
        search_query = "is:unread label:learning"

    logger.info(f"Starting agent with query: '{search_query}'")

    # Initialize Services
    gmail = GmailService()

    emails = gmail.fetch_emails(query=search_query)

    if emails:
        llm = LLMService()
        notes = NotesService()

    emails_to_process = emails[: args.limit]

    def process_email(email):
        logger.info(f"Processing email: '{email['subject']}'")

        logger.debug("Generating markdown notes via Gemini...")

        generated_notes = llm.generate_notes(email["subject"], email["content"])
        if not generated_notes:
            logger.error(
                f"Failed to generate notes for '{email['subject']}'. Skipping."
            )
            return False

        logger.debug("Proofreading generated notes via Gemini...")
        proofread_notes = llm.proofread_notes(email["content"], generated_notes)
        if not proofread_notes:
            logger.warning(
                f"Failed to proofread notes for '{email['subject']}'. Using unproofread version."
            )
            proofread_notes = generated_notes

        final_output = f"{proofread_notes}\n\n---\n*Tags: #ai-agent #email-notes*"

        # Save to Microsoft OneNote
        success = notes.save_note(email["subject"], final_output)

        if success:
            gmail.mark_as_read(email["id"])
            return True
        return False

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_email, emails_to_process))

    processed_count = sum(1 for r in results if r)
    logger.info(f"Job complete. Processed {processed_count} new emails.")


if __name__ == "__main__":
    main()
