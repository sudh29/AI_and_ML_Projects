import os
import argparse
import logging
from dotenv import load_dotenv
from services.gmail_service import GmailService
from services.llm_service import LLMService
from services.notes_service import NotesService

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_DIR = "data"
PROCESSED_FILE = os.path.join(DB_DIR, "processed_ids.txt")

def load_processed_ids():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, 'r') as f:
        return set(line.strip() for line in f)

def mark_as_processed(email_id):
    os.makedirs(DB_DIR, exist_ok=True)
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{email_id}\n")

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="AI Agent to turn Emails into Apple Notes")
    parser.add_argument('--query', type=str, default="is:unread label:learning", 
                        help='Gmail search query (e.g., "from:newsletter@tech.com")')
    parser.add_argument('--limit', type=int, default=5, 
                        help='Maximum number of emails to process in one run')
    args = parser.parse_args()

    logger.info(f"Starting agent with query: '{args.query}'")

    # Initialize Services
    gmail = GmailService()
    llm = LLMService()
    notes = NotesService()
    
    processed_ids = load_processed_ids()
    emails = gmail.fetch_emails(query=args.query)
    
    processed_count = 0
    
    for email in emails:
        if email['id'] in processed_ids:
            continue
            
        if processed_count >= args.limit:
            logger.info("Reached processing limit for this run.")
            break
            
        logger.info(f"Processing email: {email['subject']}")
        
        # 1. Generate structured notes
        generated_notes = llm.generate_notes(email['subject'], email['content'])
        
        # 2. Add custom tags for easy searching in Apple Notes
        final_output = f"{generated_notes}\n\n---\n*Tags: #ai-agent #email-notes*"
        
        # 3. Save to Apple Notes
        success = notes.save_to_apple_notes(email['subject'], final_output)
        
        if success:
            mark_as_processed(email['id'])
            processed_count += 1
            
    logger.info(f"Job complete. Processed {processed_count} new emails.")

if __name__ == "__main__":
    main()