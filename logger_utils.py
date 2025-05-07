# logger_utils.py

import logging
import os


def setup_logger(name: str, log_path: str = "requests.log") -> logging.Logger:
    """
    Set up and return a logger with the given name and log file path.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        os.makedirs(os.path.dirname(log_path), exist_ok=True) if os.path.dirname(
            log_path
        ) else None
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return logger
