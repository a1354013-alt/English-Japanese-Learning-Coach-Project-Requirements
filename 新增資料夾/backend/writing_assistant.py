"""
Writing Assistant Service for Language Coach
Handles AI-powered writing analysis and feedback
"""
import json
from typing import Dict, Any, Optional
from ollama_client import ollama_client
from models import WritingSubmission, WritingAnalysis
from config import settings

class WritingAssistant:
    """Service for analyzing user writing and providing feedback"""
    
    def __init__(self):
        self.client = ollama_client

    async def analyze_writing(self, submission: WritingSubmission) -> Optional[WritingAnalysis]:
        """
        Analyze user writing using AI
        """
        system_prompt = self._get_system_prompt(submission.language)
        prompt = self._get_analysis_prompt(submission)
        
        # Use a larger model for writing analysis if available
        model = settings.model_name # Default to main model
        
        result = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            format="json"
        )
        
        if not result.get("success"):
            return None
            
        analysis_data = self.client.parse_json_response(result["response"])
        if not analysis_data:
            return None
            
        try:
            # Ensure all required fields are present
            analysis_data["original_text"] = submission.text
            return WritingAnalysis(**analysis_data)
        except Exception as e:
            print(f"Error parsing writing analysis: {e}")
            return None

    def _get_system_prompt(self, language: str) -> str:
        lang_name = "English" if language == "EN" else "Japanese"
        level_system = "CEFR (A1-C2)" if language == "EN" else "JLPT (N5-N1)"
        
        return f"""You are an expert {lang_name} language tutor. 
Your task is to analyze a student's writing and provide detailed, constructive feedback.
You must evaluate the writing based on grammar, vocabulary, and style.
Provide an estimated level using the {level_system} scale.
Identify specific errors and provide corrections with explanations.
Your response MUST be in JSON format.
"""

    def _get_analysis_prompt(self, submission: WritingSubmission) -> str:
        lang_name = "English" if submission.language == "EN" else "Japanese"
        topic_info = f"Topic: {submission.topic}" if submission.topic else "Topic: General"
        target_info = f"Target Level: {submission.target_level}" if submission.target_level else ""
        
        return f"""Analyze the following {lang_name} text:
---
{submission.text}
---
{topic_info}
{target_info}

Please provide the analysis in the following JSON structure:
{{
    "corrected_text": "The full text with all corrections applied",
    "grammar_score": 0-100,
    "vocabulary_score": 0-100,
    "style_score": 0-100,
    "overall_score": 0-100,
    "estimated_level": "e.g., B2 or N3",
    "corrections": [
        {{
            "original": "incorrect part",
            "corrected": "corrected part",
            "explanation": "why it was wrong and how to fix it",
            "type": "grammar/vocabulary/spelling/style"
        }}
    ],
    "suggestions": ["suggestion 1", "suggestion 2"],
    "feedback": "Overall encouraging feedback and summary of strengths/weaknesses"
}}
"""

writing_assistant = WritingAssistant()
