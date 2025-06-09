# logger_utils.py

import logging
import os

# Default log path within the repository root
LOG_PATH = os.path.join(os.path.dirname(__file__), "requests.log")


def setup_logger(name: str, log_path: str | None = None) -> logging.Logger:
    """
    Set up and return a logger with the given name and log file path.
    """
    logger = logging.getLogger(name)
    if log_path is None:
        log_path = LOG_PATH
    if not logger.handlers:
        if os.path.dirname(log_path):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return logger

if __name__ == "__main__":
    # setup_logger(name="app_logger")
    logger = setup_logger(name="app_logger")
    logger.info(f"Successfully set up {logger}")
