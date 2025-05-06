import os
import openai
import requests
import logging
from dotenv import load_dotenv
from gpt_utils import count_tokens, log_request

from rich.console import Console

console = Console()


class RadioFreeDJ:
    def __init__(
        self,
        api_key=None,
        active_model=None,
        log_path="requests.log",
        system_prompt=None,
        on_response=None,
    ):
        # Load environment vars once
        load_dotenv()

        # Core config
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.active_model = active_model or os.getenv("GPT_MODEL", "gpt-4o-mini")
        self.log_path = os.path.abspath(log_path)

        # System prompt for chat completions
        self.system_prompt = system_prompt or os.getenv("SYSTEM_PROMPT", "")

        # Optional callback for (prompt, response)
        self.on_response = on_response

        # Local LLM support
        use_local = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        self.use_local_llm = use_local
        self.local_llm_url = os.getenv("LOCAL_LLM_API")

        if not self.use_local_llm and not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set and local LLM is not enabled.")

        # Apply API key for OpenAI
        if not self.use_local_llm:
            openai.api_key = self.api_key

        # Logger to the same log_path
        self.logger = logging.getLogger("RadioFreeDJ")
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
            )
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(handler)

    def count_tokens(self, prompt: str) -> int:
        try:
            return count_tokens(prompt, self.active_model)
        except Exception as e:
            console.print(f"[red]Token count error:[/red] {e}")
            return 0

    def log_request(self, prompt: str, token_count: int):
        log_request(prompt, self.active_model, token_count, self.log_path)

    def ask(self, prompt: str) -> str | None:
        token_count = self.count_tokens(prompt)
        self.log_request(prompt, token_count)

        try:
            if self.use_local_llm:
                response = self._ask_local(prompt)
            else:
                response = self._ask_openai(prompt)

            # Debug log
            self.logger.debug(f"Response received:\n{response}")

            # Callback to track in UI
            if self.on_response:
                try:
                    self.on_response(prompt, response)
                except Exception as cb_err:
                    self.logger.error(f"on_response callback error: {cb_err}")

            return response

        except Exception as e:
            self.logger.error(f"Error getting GPT response: {e}")
            return None

    def _ask_openai(self, prompt: str) -> str:
        # Assemble messages with optional system role
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        api_resp = openai.ChatCompletion.create(
            model=self.active_model,
            messages=messages,
        )
        return api_resp.choices[0].message.content.strip()

    def _ask_local(self, prompt: str) -> str:
        if not self.local_llm_url:
            raise ValueError("LOCAL_LLM_API is not set in .env")

        payload = {"model": self.active_model, "messages": []}
        if self.system_prompt:
            payload["messages"].append(
                {"role": "system", "content": self.system_prompt}
            )
        payload["messages"].append({"role": "user", "content": prompt})

        resp = requests.post(self.local_llm_url, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
