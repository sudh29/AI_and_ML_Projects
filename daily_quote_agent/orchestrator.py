import logging
from dataclasses import dataclass
from formatter import Formatter
from db_utils import log_post

logger = logging.getLogger("quote-agent")


@dataclass
class Candidate:
    quote: str
    author: str
    caption: str
    hashtags: str


class Orchestrator:
    def __init__(self, llm_client, validator, publisher):
        self.llm = llm_client
        self.validator = validator
        self.publisher = publisher

    def run_once(self, prompt: str, dry_run: bool = False):
        MAX_GENERATION_ATTEMPTS = 5
        attempts = 0
        while attempts < MAX_GENERATION_ATTEMPTS:
            attempts += 1
            logger.info("Generation attempt %d for prompt: %s", attempts, prompt)
            cand = self.llm.generate_quote_candidate(prompt)
            quote = cand.get("quote", "").strip()
            author = cand.get("author", "").strip()
            caption = cand.get("caption", "").strip()
            hashtags = cand.get("hashtags", "").strip()

            if not quote:
                logger.warning("LLM returned empty quote; retrying")
                continue

            if not self.validator.is_unique(quote):
                logger.info("Quote already posted before; retrying")
                continue

            ok_author = self.validator.verify_author(quote, author)
            if not ok_author:
                logger.info(
                    "Author verification failed; retrying or suggesting correction"
                )
                continue

            candidate = Candidate(
                quote=quote, author=author, caption=caption, hashtags=hashtags
            )
            formatted = {}
            for platform in self.publisher.config.keys():
                formatted[platform] = Formatter.to_platform_text(
                    quote, caption, hashtags, platform
                )

            if dry_run:
                logger.info("Dry run: would post: %s", formatted)
                return candidate

            post_results = self.publisher.post_all(formatted)
            logger.info("Post results: %s", post_results)
            log_post(quote, author, caption, post_results)
            return candidate

        logger.error(
            "Failed to generate a valid quote after %d attempts",
            MAX_GENERATION_ATTEMPTS,
        )
        return None
