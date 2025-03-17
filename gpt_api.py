# gpt_api v.1.1.0.
import openai
import os
import json
import requests
import base64
import logging
import tiktoken
from datetime import datetime
from dotenv import load_dotenv
from config import USE_LOCAL_LLM, ANYTHING_API_URL, ANYTHING_API_KEY

# Load environment variables from .env file
project_dir = os.path.dirname(__file__)
env_path = os.path.join(project_dir, ".env")
load_dotenv(env_path)

username = os.getenv("WEBUI_USR")
password = os.getenv("WEBUI_PSWD")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key and not USE_LOCAL_LLM:
    raise ValueError("OPENAI_API_KEY environment variable not set or failed to load from .env.")

gpt_request_log_path = os.path.join(project_dir, "gpt_requests.log")
TIMESTAMP = datetime.now()
WORKSPACE_SLUG = "radiofree"

def count_tokens(prompt, model="gpt-4o-mini"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))

def log_gpt_request(prompt, api_response, token_count, log_file_path="gpt_requests.log"):
    """
    Logs detailed information about GPT interactions to the specified log file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    model_used = api_response.get("model", "Unknown Model")
    total_tokens = api_response.get("usage", {}).get("total_tokens", "Unknown")
    log_entry = (
        "\n=== GPT Interaction ===\n"
        f"Timestamp      : {timestamp}\n"
        f"Model: {model_used}\n"
        f"Request Tokens: {token_count}\n"
        f"Total Tokens Used: {total_tokens}\n\n"
        "--- PROMPT START ---\n"
        f"{prompt}\n"
        "--- PROMPT END ---\n\n"
        "--- RESPONSE START ---\n"
        f"{json.dumps(api_response, indent=2)}\n"
        "--- RESPONSE END ---\n"
        "=== END OF GPT INTERACTION ===\n"
        "\n"
    )
    try:
        with open(gpt_request_log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        logging.error(f"Error writing GPT log entry: {e}")

def call_local_llm(prompt):
    headers = {
        "Authorization": f"Bearer {ANYTHING_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": prompt,
        "mode": "chat",
        "sessionId": "RadioFree GPT",
        "attachments": []
    }
    
    endpoint = f"{ANYTHING_API_URL}/v1/workspace/{WORKSPACE_SLUG}/chat"
    response = requests.post(endpoint, headers=headers, json=payload)
    
    if response.ok:
        print(response.json())
        return response.json()
    else:
        logging.error(f"Local LLM error: {response.status_code} {response.text}")
        return None

def format_api_response(api_response):
    try:
        text = api_response.get("textResponse", "").strip()
        sources = api_response.get("sources", [])
        close = api_response.get("close", False)
        error = api_response.get("error", None)
    except Exception as e:
        logging.error(f"Error formatting API response: {e}")
        text = None
        sources = []
        close = False
        error = None
    return {
            "text": text,
            "sources": sources,
            "close": close,
            "error": error
        }

def ask_gpt(prompt):
    token_count = count_tokens(prompt, model="gpt-4o-mini")
    if USE_LOCAL_LLM:
        completions_url = f"{ANYTHING_API_URL}/v1/workspace/{WORKSPACE_SLUG}/chat"
        try:
            print(f"Sending request to EverythingLLM at: {completions_url}")
            api_response = call_local_llm(prompt)
            formatted_response = format_api_response(api_response)
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logging.error(f"Error during local web UI call: {e}")
            return None
    else:
        if not openai.api_key:
            raise RuntimeError("OpenAI API key is not set. Please check .env and environment variables.")
        try:
            api_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            formatted_response = api_response['choices'][0]['message']['content']
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logging.error(f"Error during GPT API call: {e}")
            return None

