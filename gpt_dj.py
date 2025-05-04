import os
import openai
from openai import OpenAI
import requests
import logging
from dotenv import load_dotenv
from gpt_utils import count_tokens, log_request

from rich.console import Console
from rich.panel import Panel

console = Console()


class RadioFreeDJ:
    def __init__(
        self,
        api_key=None,
        active_model=None,
        log_path="requests.log",
        on_response=None,
    ):
        load_dotenv()
        # Debug log setup
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "gpt_debug.log")
        self.logger = logging.getLogger("RadioFreeDJ")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(debug_log_path)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        )
        self.logger.addHandler(handler)

        # Core config
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.active_model = active_model or os.getenv("GPT_MODEL", "gpt-4o-mini")
        self.log_path = os.path.abspath(log_path)

        # Store the optional callback that will receive (prompt, response)
        self.on_response = on_response

        # Local vs. remote LLM toggles
        self.use_local_llm = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        self.local_llm_url = os.getenv("LOCAL_LLM_API")

        if not self.use_local_llm and not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set and local LLM is not enabled.")

        if not self.use_local_llm:
            openai.api_key = self.api_key

    def count_tokens(self, prompt):
        try:
            return count_tokens(prompt, self.active_model)
        except Exception as e:
            console.print(f"[red]Token count error:[/red] {e}")
            return 0

    def log_request(self, prompt, token_count):
        log_request(prompt, self.active_model, token_count, self.log_path)

    def ask(self, prompt):
        token_count = self.count_tokens(prompt)
        self.log_request(prompt, token_count)

        try:
            if self.use_local_llm:
                response = self.ask_local_llm(prompt)
            else:
                response = self.ask_openai(prompt)

            self.logger.debug(f"Prompt sent:\n{prompt}")
            self.logger.debug(f"Response received:\n{response}")
            return response

        except Exception as e:
            error_msg = f"Error getting GPT response: {e}"
            self.logger.error(error_msg)
            return None

    def ask_openai(self, prompt):
        client = OpenAI(api_key=self.api_key)

        response = client.chat.completions.create(
            model=self.active_model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content.strip()

    def ask_local_llm(self, prompt):
        if not self.local_llm_url:
            raise ValueError("LOCAL_LLM_API not set in .env")

        payload = {
            "model": self.active_model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(self.local_llm_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
