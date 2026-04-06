"""
Study Planner Service for Language Coach
Generates personalized study plans based on goals and progress
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from ollama_client import ollama_client
from models import StudyPlan, StudyMilestone
from config import settings

class StudyPlanner:
    """Service for generating personalized study plans"""
    
    def __init__(self):
        self.client = ollama_client

    async def generate_plan(self, user_id: str, target_goal: str, language: str, current_progress: Dict[str, Any]) -> Optional[StudyPlan]:
        """
        Generate a personalized study plan using AI
        """
        system_prompt = f"You are an expert language learning consultant specializing in {language}."
        prompt = self._get_plan_prompt(target_goal, language, current_progress)
        
        result = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            format="json"
        )
        
        if not result.get("success"):
            return None
            
        plan_data = self.client.parse_json_response(result["response"])
        if not plan_data:
            return None
            
        try:
            # Post-process dates
            start_date = datetime.now()
            # AI might return end_date as string, convert to datetime
            if isinstance(plan_data.get("end_date"), str):
                try:
                    plan_data["end_date"] = datetime.fromisoformat(plan_data["end_date"].replace('Z', '+00:00'))
                except:
                    plan_data["end_date"] = start_date + timedelta(days=90) # Default 3 months
            
            # Process milestones
            milestones = []
            for m in plan_data.get("milestones", []):
                if isinstance(m.get("target_date"), str):
                    try:
                        m["target_date"] = datetime.fromisoformat(m["target_date"].replace('Z', '+00:00'))
                    except:
                        m["target_date"] = start_date + timedelta(days=30)
                milestones.append(StudyMilestone(**m))
            
            plan_data["milestones"] = milestones
            plan_data["user_id"] = user_id
            plan_data["target_goal"] = target_goal
            plan_data["language"] = language
            
            return StudyPlan(**plan_data)
        except Exception as e:
            print(f"Error parsing study plan: {e}")
            return None

    def _get_plan_prompt(self, target_goal: str, language: str, progress: Dict[str, Any]) -> str:
        lang_name = "English" if language == "EN" else "Japanese"
        curr_level = progress.get('current_level', 'Beginner')
        
        return f"""Create a detailed, personalized {lang_name} study plan for a student.
Student's Current Level: {curr_level}
Student's Target Goal: {target_goal}
Current Stats: {progress.get('completed_lessons', 0)} lessons completed, {progress.get('accuracy_rate', 0)}% accuracy.

The plan should be realistic and broken down into milestones.
Your response MUST be in JSON format.

JSON Structure:
{{
    "end_date": "YYYY-MM-DDTHH:MM:SS (estimated completion date)",
    "daily_commitment_minutes": 30-60,
    "focus_areas": ["area 1", "area 2", "area 3"],
    "milestones": [
        {{
            "title": "Milestone Title",
            "description": "What to achieve in this phase",
            "target_date": "YYYY-MM-DDTHH:MM:SS",
            "required_skills": ["skill 1", "skill 2"]
        }}
    ]
}}
"""

study_planner = StudyPlanner()
