import os
from openai import OpenAI


class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing.")
        self.client = OpenAI(api_key=api_key)

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
            response = self.client.chat.completions.create(
                model="gpt-4o",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Subject: {subject}\n\nContent:\n{content}",
                    },
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating notes with OpenAI: {e}")
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
            response = self.client.chat.completions.create(
                model="gpt-4o",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Original Content:\n{original_content}\n\nGenerated Notes:\n{generated_notes}",
                    },
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error proofreading notes with OpenAI: {e}")
            return generated_notes
