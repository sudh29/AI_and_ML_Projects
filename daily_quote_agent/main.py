import os
import logging
import time
import argparse
import schedule
from db_utils import ensure_db
from llm_client import LLMClient
from validator import QuoteValidator
from publisher import Publisher
from orchestrator import Orchestrator

# Social platform placeholders
SOCIAL_CONFIG = {
    "twitter": {"enabled": False, "api_key": os.environ.get("TW_API_KEY", "")},
    "facebook": {"enabled": False, "api_key": os.environ.get("FB_API_KEY", "")},
    "instagram": {"enabled": False, "api_key": os.environ.get("IG_API_KEY", "")},
    # "linkedin": {"enabled": False, "api_key": os.environ.get("LI_API_KEY", "")},
}

POST_TIME_HHMM = os.environ.get("POST_TIME", "09:00")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("quote-agent")


def main():
    parser = argparse.ArgumentParser(
        description="Daily Creative Quote Poster Agent (modular)"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Provide a short famous quote plus author and an engaging caption. Choose diverse famous sources.",
        help="Prompt for the LLM",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not post; only generate and validate"
    )
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit (useful for scheduler)"
    )
    args = parser.parse_args()

    ensure_db()
    llm = LLMClient(provider=LLM_PROVIDER)
    val = QuoteValidator()
    pub = Publisher(SOCIAL_CONFIG)
    orch = Orchestrator(llm, val, pub)

    if args.once:
        orch.run_once(args.prompt, dry_run=args.dry_run)
    else:
        try:

            def job():
                orch.run_once(args.prompt, dry_run=args.dry_run)

            schedule.every().day.at(POST_TIME_HHMM).do(job)
            logger.info("Scheduled daily job at %s", POST_TIME_HHMM)
            while True:
                schedule.run_pending()
                time.sleep(10)
        except Exception:
            logger.info("Schedule library not used; running once")
            orch.run_once(args.prompt, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
