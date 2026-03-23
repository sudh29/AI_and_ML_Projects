import logging

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

import constants

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self) -> None:
        api_key = constants.GEMINI_API_KEY
        if not api_key:
            raise ValueError(
                "Missing GEMINI_API_KEY environment variable. "
                "Please add your Gemini API key to your .env file: GEMINI_API_KEY=your_key_here. "
                "Get your API key from Google AI Studio: https://aistudio.google.com/app/apikey"
            )
        try:
            self.client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=int(constants.GEMINI_REQUEST_TIMEOUT * 1000),
                ),
            )
        except Exception as e:
            raise Exception(
                f"Failed to initialize Gemini client: {e}. "
                "Ensure your GEMINI_API_KEY is valid and that you have API access."
            )

    @retry(
        stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_gemini(
        self, system_instruction: str, contents: str, temperature: float
    ) -> str:
        response = self.client.models.generate_content(
            model=constants.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )
        return response.text

    def select_skill(self, subject: str, content: str) -> str:
        """Dynamically selects the best markdown persona file based on the email context."""

        if not constants.SKILLS_DIR.exists():
            return constants.DEFAULT_SKILL

        skill_files = [f.name for f in constants.SKILLS_DIR.glob("*.md")]
        if not skill_files:
            return constants.DEFAULT_SKILL

        # Build the structured output schema as a plain dict to avoid
        # re-creating a Pydantic model on every invocation.
        skill_schema = {
            "type": "object",
            "properties": {
                "skill_filename": {
                    "type": "string",
                    "description": (
                        f"The exact filename of the skill to use from this list: "
                        f"{skill_files}. If none match well, return '{constants.DEFAULT_SKILL}'."
                    ),
                }
            },
            "required": ["skill_filename"],
        }

        prompt = f"""
        You are an intelligent routing agent.
        Your job is to read the subject and summary of an email and determine which of the available 'skill' personas is best suited for summarizing it.
        
        Available Skills:
        {", ".join(skill_files)}
        
        Email Subject: {subject}
        Email Content Snippet:
        {content}
        
        Select the filename of the most appropriate skill.
        """

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=5),
        )
        def _fetch_skill():
            response = self.client.models.generate_content(
                model=constants.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=skill_schema,
                    temperature=0.0,
                ),
            )

            chosen_file = None
            if getattr(response, "parsed", None):
                if isinstance(response.parsed, dict):
                    chosen_file = response.parsed.get("skill_filename")
                else:
                    chosen_file = getattr(response.parsed, "skill_filename", None)

            if not chosen_file and getattr(response, "text", None):
                import json

                try:
                    data = json.loads(response.text)
                    chosen_file = data.get("skill_filename")
                except json.JSONDecodeError:
                    pass

            if not chosen_file or chosen_file not in skill_files:
                return constants.DEFAULT_SKILL
            return chosen_file

        try:
            return _fetch_skill()
        except Exception as e:
            logger.warning(
                "Error selecting skill dynamically after retries: %s. Defaulting to %s.",
                e,
                constants.DEFAULT_SKILL,
            )
            return constants.DEFAULT_SKILL

    def generate_notes(self, subject: str, content: str) -> str | None:
        """Transforms raw email text into structured learning notes."""
        chosen_skill = self.select_skill(subject, content)
        logger.info("Dynamically routed '%s' to persona: %s", subject, chosen_skill)

        skill_path = constants.SKILLS_DIR / chosen_skill
        try:
            system_prompt = skill_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(
                "Skill file '%s' not found. Falling back to default prompt.",
                chosen_skill,
            )
            system_prompt = constants.PROMPT_GENERATE_NOTES
        except UnicodeDecodeError as e:
            logger.warning(
                "Skill file '%s' has invalid encoding (%s). Falling back to default prompt.",
                chosen_skill,
                e,
            )
            system_prompt = constants.PROMPT_GENERATE_NOTES
        except Exception as e:
            logger.warning(
                "Failed to load skill file '%s' (%s). Falling back to default prompt.",
                chosen_skill,
                e,
            )
            system_prompt = constants.PROMPT_GENERATE_NOTES

        try:
            return self._call_gemini(
                system_prompt,
                f"Subject: {subject}\n\nContent:\n{content}",
                0.3,
            )
        except Exception as e:
            inner_error = e
            # Unpack tenacity RetryError to find the actual ClientError
            if hasattr(e, "last_attempt") and getattr(
                e.last_attempt, "exception", None
            ):
                inner_err = e.last_attempt.exception()
                if inner_err:
                    inner_error = inner_err
            logger.error(
                "Error generating notes with Gemini after retries. Inner error: %s",
                inner_error,
            )
            return None

    def proofread_notes(
        self, original_content: str, generated_notes: str
    ) -> str | None:
        """Proofreads generated notes against the original email content.

        Ensures the generated notes are 100% accurate, capture all key details,
        and do not contain any hallucinations by comparing against the original.

        Args:
            original_content: The raw email content to verify against.
            generated_notes: The AI-generated notes to proofread.

        Returns:
            The proofread notes, or None if proofreading fails after retries.
        """
        try:
            return self._call_gemini(
                constants.PROMPT_PROOFREAD_NOTES,
                f"Original Content:\n{original_content}\n\nGenerated Notes:\n{generated_notes}",
                0.2,
            )
        except Exception as e:
            inner_error = e
            if hasattr(e, "last_attempt") and getattr(
                e.last_attempt, "exception", None
            ):
                inner_err = e.last_attempt.exception()
                if inner_err:
                    inner_error = inner_err
            logger.error(
                "Error proofreading notes with Gemini after retries. Inner error: %s",
                inner_error,
            )
            return None
