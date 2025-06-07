

import os
import openai
from openai import OpenAIError
import requests
import logging
from dotenv import load_dotenv
from gpt_utils import count_tokens
from logger_utils import setup_logger
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

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
        load_dotenv()

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.active_model = active_model or os.getenv("GPT_MODEL", "gpt-4o")
        self.log_path = os.path.abspath(log_path)
        self.system_prompt = system_prompt or os.getenv("SYSTEM_PROMPT", "")
        self.on_response = on_response

        use_local = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        self.use_local_llm = use_local
        self.local_llm_url = os.getenv("LOCAL_LLM_API")

        if not self.use_local_llm and not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set and local LLM is not enabled.")

        if not self.use_local_llm:
            self.client = openai.OpenAI(api_key=self.api_key)

        self.logger = setup_logger("RadioFreeDJ", self.log_path)

        # For toggling logs view
        self.show_logs = False

    def count_tokens(self, prompt: str) -> int:
        try:
            return count_tokens(prompt, self.active_model)
        except Exception as e:
            console.print(f"[red]Token count error:[/red] {e}")
            return 0

    def ask(self, prompt: str) -> str | None:
        token_count = self.count_tokens(prompt)
        self.logger.debug(f"Prompt sent ({token_count} tokens):\n{prompt}")
        
        console.print(f"[cyan]🔍 Sending to GPT model:[/cyan] {self.active_model}")
        console.print(Panel(prompt, title="🧠 GPT Prompt"))

        try:
            response = self._ask_local(prompt) if self.use_local_llm else self._ask_openai(prompt)
            self.logger.info(f"Response for prompt:\n{response}")
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
        try:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.active_model,
                messages=messages
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            self.logger.error(f"OpenAI request failed: {e}")
            console.print(Panel(str(e), title="❌ GPT API Error", border_style="red"))
            return "[gpt-error]"
        except Exception as e:
            self.logger.error(f"Unexpected error during OpenAI call: {e}")
            console.print(Panel(str(e), title="❌ GPT Error", border_style="red"))
            return "[gpt-error]"


    def _ask_local(self, prompt: str) -> str:
        if not self.local_llm_url:
            raise ValueError("LOCAL_LLM_API is not set in .env")

        payload = {"model": self.active_model, "messages": []}
        if self.system_prompt:
            payload["messages"].append({"role": "system", "content": self.system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})

        resp = requests.post(self.local_llm_url, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def toggle_log_view(self):
        self.show_logs = not self.show_logs

    def render_log_panel(self) -> Panel:
        if not self.show_logs:
            return Panel("[dim]Logs hidden. Toggle with 'v'.[/dim]", title=" Logs", border_style="gray")
        try:
            if os.path.exists(self.log_path):
                with open(self.log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-20:]
                text = Text("".join(lines), style="green")
            else:
                text = Text("[No log file found]", style="red")
        except Exception as e:
            text = Text(f"Error reading log file: {e}", style="red")
        return Panel(text, title=" Logs", border_style="gray")

