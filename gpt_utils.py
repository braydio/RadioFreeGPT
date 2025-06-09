import logging
import tiktoken
from rich.console import Console
from rich.panel import Panel
from logger_utils import setup_logger

console = Console()
logger = setup_logger(__name__)


def count_tokens(prompt, active_model):
    try:
        encoding = tiktoken.encoding_for_model(active_model)
        return len(encoding.encode(prompt))
    except Exception as e:
        logger.error("Token count error: %s", e)
        console.print(Panel(str(e), title=" Token Count Error", border_style="red"))
        return len(prompt.split())


def log_request(prompt, active_model, token_count):
    try:
        logger.info("--- RadioFreeGPT Request ---")
        logger.info("Model: %s", active_model)
        logger.info("Prompt:\n%s", prompt)
        logger.info("Tokens used: %s", token_count)
    except Exception as e:
        logger.error("Log write error: %s", e)
        console.print(Panel(str(e), title=" Log Write Error", border_style="red"))
