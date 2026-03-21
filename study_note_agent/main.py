import argparse
import logging
from dotenv import load_dotenv
from services.gmail_service import GmailService
from services.llm_service import LLMService
from services.notes_service import NotesService
import constants

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
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
    llm = LLMService()
    notes = NotesService()

    emails = gmail.fetch_emails(query=search_query)

    processed_count = 0

    for email in emails:
        if processed_count >= args.limit:
            logger.info("Reached processing limit for this run.")
            break

        logger.info(f"Processing email: {email['subject']}")

        # 1. Generate structured notes
        generated_notes = llm.generate_notes(email["subject"], email["content"])
        if not generated_notes:
            logger.error(f"Failed to generate notes for {email['subject']}. Skipping.")
            continue

        # 2. Proofread generated notes
        logger.info(f"Proofreading notes for: {email['subject']}")
        proofread_notes = llm.proofread_notes(email["content"], generated_notes)
        if not proofread_notes:
            logger.error(
                f"Failed to proofread notes for {email['subject']}. Using unproofread version."
            )
            proofread_notes = generated_notes

        # 3. Add custom tags for easy searching in Apple Notes
        final_output = f"{proofread_notes}\n\n---\n*Tags: #ai-agent #email-notes*"

        # 4. Save to Apple Notes
        success = notes.save_to_apple_notes(email["subject"], final_output)

        if success:
            # Mark email as read via Gmail API so it isn't picked up again
            gmail.mark_as_read(email["id"])
            processed_count += 1

    logger.info(f"Job complete. Processed {processed_count} new emails.")


if __name__ == "__main__":
    main()
