import os
import json
import logging
import openai

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
logger = logging.getLogger("quote-agent")


class LLMClient:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        if provider == "openai":
            try:
                openai.api_key = OPENAI_API_KEY
                self.openai = openai
            except Exception as e:
                logger.warning("OpenAI library not available or API key missing: %s", e)
                self.openai = None
        else:
            self.openai = None

    def generate_quote_candidate(self, prompt: str, temperature: float = 0.8) -> dict:
        system_prompt = (
            "You are an assistant that returns a single short famous quote, its correct author, "
            "a 1-line engaging social caption, and a few hashtags. Output JSON with keys: quote, author, caption, hashtags."
        )
        user_prompt = f"Task: {prompt}\nRespond only with valid JSON."

        if self.provider == "openai" and self.openai is not None:
            resp = self.openai.ChatCompletion.create(
                model=(
                    "gpt-4o-mini"
                    if hasattr(self.openai, "ChatCompletion")
                    else "gpt-4o-mini"
                ),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=200,
            )
            text = resp["choices"][0]["message"]["content"]
            try:
                j = json.loads(text)
                return j
            except Exception:
                return {
                    "quote": text.strip(),
                    "author": "",
                    "caption": "",
                    "hashtags": "",
                }
        else:
            return {
                "quote": "The only limit to our realization of tomorrow is our doubts of today.",
                "author": "Franklin D. Roosevelt",
                "caption": "Believe in tomorrow — take small steps today.",
                "hashtags": "#inspiration #motivation",
            }
