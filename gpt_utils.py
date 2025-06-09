import logging
import tiktoken
from rich.console import Console
from rich.panel import Panel
from logger_utils import setup_logger
import json
import re

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


def parse_json_response(text: str):
    """Extract and parse the first JSON object found in *text*.

    Returns a dictionary if successful, otherwise ``None``.
    """
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if not match:
            logger.warning("No JSON object detected in response")
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            logger.error("JSON decode error: %s", e)
            return None
