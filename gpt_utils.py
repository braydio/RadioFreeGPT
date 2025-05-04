import os
import tiktoken
from rich.console import Console
from rich.panel import Panel

console = Console()


def count_tokens(prompt, active_model):
    try:
        encoding = tiktoken.encoding_for_model(active_model)
        return len(encoding.encode(prompt))
    except Exception as e:
        console.print(Panel(str(e), title=" Token Count Error", border_style="red"))
        return len(prompt.split())


def log_request(prompt, active_model, token_count, log_path="radio.log"):
    try:
        log_path = os.path.abspath(log_path)
        with open(log_path, "a") as log_file:
            log_file.write(f"\n--- RadioFreeGPT Request ---\n")
            log_file.write(f"Model: {active_model}\n")
            log_file.write(f"Prompt:\n{prompt}\n")
            log_file.write(f"Tokens used: {token_count}\n")
            log_file.write(f"-----------------------------\n")
        console.print(f"[green] Logged request to:[/green] {log_path}")
    except Exception as e:
        console.print(Panel(str(e), title=" Log Write Error", border_style="red"))
