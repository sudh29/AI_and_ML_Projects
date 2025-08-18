import logging

logger = logging.getLogger("quote-agent")


class Publisher:
    def __init__(self, config):
        self.config = config

    def post_to_twitter(self, text: str) -> bool:
        logger.info("Posting to Twitter (placeholder)")
        return True

    def post_to_facebook(self, text: str) -> bool:
        logger.info("Posting to Facebook (placeholder)")
        return True

    def post_to_instagram(self, text: str) -> bool:
        logger.info("Posting to Instagram (placeholder)")
        return True

    def post_all(self, formatted_texts: dict) -> dict:
        results = {}
        for platform, text in formatted_texts.items():
            if not self.config.get(platform, {}).get("enabled"):
                results[platform] = False
                continue
            try:
                if platform == "twitter":
                    results[platform] = self.post_to_twitter(text)
                elif platform == "facebook":
                    results[platform] = self.post_to_facebook(text)
                elif platform == "instagram":
                    results[platform] = self.post_to_instagram(text)
                else:
                    results[platform] = False
            except Exception as e:
                logger.exception("Posting to %s failed: %s", platform, e)
                results[platform] = False
        return results
