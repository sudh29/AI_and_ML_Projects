import os
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

MODEL = "gemini-2.5-flash"


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
        system_prompt = """
        You are an expert technical summarizer and educator. 
        Your job is to read an email and extract the valuable information into structured, revision-friendly notes.
        Ignore pleasantries, disclaimers, signatures, and logistical noise.
        
        Format your response in Markdown using exactly this structure:
        # [Email Subject]
        
        ## Summary
        [2-3 sentence high-level overview]
        
        ## Key Concepts
        * [Concept 1]: [Brief explanation]
        * [Concept 2]: [Brief explanation]
        
        ## Detailed Notes
        [Organized bullet points containing the core information, examples, and technical details]
        
        ## Quick Revision
        [3-4 rapid-fire Q&A style points or a TL;DR for quick memory recall]
        """
        try:
            return self._call_gemini(
                system_prompt, f"Subject: {subject}\n\nContent:\n{content}", 0.3
            )
        except Exception as e:
            print(f"Error generating notes with Gemini after retries: {e}")
            return None

    def proofread_notes(
        self, original_content: str, generated_notes: str
    ) -> str | None:
        """Acts as a reviewer to ensure the generated notes are accurate based on the original content."""
        system_prompt = """
        You are an expert technical reviewer.
        Your job is to read the original email content and the generated structured notes, 
        and proofread the notes to ensure they are 100% accurate, capture all key details, 
        and do not contain any hallucinations.
        
        Fix any inaccuracies, grammatical errors, or missing critical details. 
        Return ONLY the finalized, corrected Markdown notes in the exact same format.
        """
        try:
            return self._call_gemini(
                system_prompt,
                f"Original Content:\n{original_content}\n\nGenerated Notes:\n{generated_notes}",
                0.2,
            )
        except Exception as e:
            print(f"Error proofreading notes with Gemini after retries: {e}")
            return generated_notes
