import logging.config


def setup_logging():
    """Configures project-wide logging format and suppresses noisy third-party libraries."""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "default": {
                "level": "WARNING",
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": True,
            },
            "__main__": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False,
            },
            "agent": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False,
            },
            "services": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)
