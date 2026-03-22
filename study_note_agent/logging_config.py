import logging


def setup_logging():
    """Configures project-wide logging format and suppresses noisy third-party libraries."""

    # Force the global root logger to WARNING so NO rogue third-party libraries can leak INFO logs.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Explicitly re-enable INFO logs strictly for our own internal application modules
    logging.getLogger("__main__").setLevel(logging.INFO)
    logging.getLogger("services").setLevel(logging.INFO)
