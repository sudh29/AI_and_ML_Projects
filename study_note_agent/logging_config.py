import logging


def setup_logging():
    """Configures project-wide logging format and suppresses noisy third-party libraries."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Suppress incredibly noisy third-party HTTP and API connection logs
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.WARNING)
    logging.getLogger("google.genai._api_client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("msal").setLevel(logging.WARNING)
