import os
import logging
import constants
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

MODEL = "gemini-2.5-flash"
logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
        self.client = genai.Client(api_key=api_key)

    @retry(
        stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_gemini(
        self, system_instruction: str, contents: str, temperature: float
    ) -> str:
        response = self.client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )
        return response.text

    def generate_notes(self, subject: str, content: str) -> str | None:
        """Transforms raw email text into structured learning notes."""
        try:
            return self._call_gemini(
                constants.PROMPT_GENERATE_NOTES,
                f"Subject: {subject}\n\nContent:\n{content}",
                0.3,
            )
        except Exception as e:
            logger.error(f"Error generating notes with Gemini after retries: {e}")
            return None

    def proofread_notes(
        self, original_content: str, generated_notes: str
    ) -> str | None:
        """Acts as a reviewer to ensure the generated notes are accurate based on the original content."""
        try:
            return self._call_gemini(
                constants.PROMPT_PROOFREAD_NOTES,
                f"Original Content:\n{original_content}\n\nGenerated Notes:\n{generated_notes}",
                0.2,
            )
        except Exception as e:
            logger.error(f"Error proofreading notes with Gemini after retries: {e}")
            return generated_notes
