import os
from openai import OpenAI

class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing.")
        self.client = OpenAI(api_key=api_key)

    def generate_notes(self, subject: str, content: str) -> str:
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
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Subject: {subject}\n\nContent:\n{content}"}
            ]
        )
        
        return response.choices[0].message.content