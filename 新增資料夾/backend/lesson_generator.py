"""
Lesson generator using Ollama AI
Generates structured language learning content with Fallback and Smart Scheduling
"""
import json
import os
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional, Literal
from uuid import uuid4

from ollama_client import ollama_client
from models import Lesson, LessonMetadata, VocabularyItem, GrammarSection, ReadingSection, DialogueSection, TaskStatus
from database import db
from config import settings


class LessonGenerator:
    """Generate language learning lessons using AI with Robustness and Intelligence"""
    
    # Topic pools for random selection
    ENGLISH_TOPICS = [
        "Daily Conversation", "Business Communication", "Travel & Tourism",
        "Technology & Innovation", "Health & Wellness", "Food & Cooking",
        "Environment & Sustainability", "Education & Learning", "Arts & Culture",
        "Sports & Fitness", "Finance & Economy", "Social Media & Internet"
    ]
    
    JAPANESE_TOPICS = [
        "日常会話", "ビジネス日本語", "旅行と観光",
        "テクノロジー", "健康とウェルネス", "料理と食文化",
        "環境問題", "教育", "芸術と文化",
        "スポーツ", "經濟とビジネス", "インターネットとSNS"
    ]
    
    def __init__(self):
        self.ollama = ollama_client
    
    def _get_system_prompt(self, language: Literal["EN", "JP"]) -> str:
        if language == "EN":
            return """You are an expert English language teacher specializing in TOEIC preparation.
Generate comprehensive, structured English lessons in valid JSON format.
All content must be educational, accurate, and appropriate for the specified CEFR level."""
        else:
            return """You are an expert Japanese language teacher specializing in JLPT preparation.
Generate comprehensive, structured Japanese lessons in valid JSON format.
Include proper hiragana readings for kanji."""

    def _select_smart_model(self, language: str, level: str, context_len: int) -> str:
        """Select model based on user level, task complexity, and language"""
        # Japanese often works better with specific small models or large models
        if language == "JP":
            return settings.large_model_name
        
        # For advanced users or long contexts, use the big model
        if level in ["C1", "C2", "N1"] or context_len > 1000:
            return settings.large_model_name
            
        return settings.small_model_name

    def _build_english_prompt(self, level: str, topic: str) -> str:
        return f"""Generate a structured English lesson for level {level} on the topic of '{topic}'.
        The JSON must include:
        1. vocabulary: 10-15 items with word, phonetic, definition_zh, example_sentence, example_translation.
        2. grammar: title, explanation, 3-5 examples, 5 exercises (question, options, correct_answer, explanation).
        3. reading: title, content (300-450 words), word_count, 5 comprehension questions.
        4. dialogue: scenario, context, 8-12 lines of dialogue (role, text, translation), 3-5 alternatives.
        
        Ensure the JSON is valid and follows the schema strictly."""

    def _build_japanese_prompt(self, level: str, topic: str) -> str:
        return f"""Generate a structured Japanese lesson for level {level} on the topic of '{topic}'.
        The JSON must include:
        1. vocabulary: 10-15 items with word, reading (hiragana), definition_zh, example_sentence, example_translation.
        2. grammar: title, explanation, 3-5 examples, 5 exercises (question, options, correct_answer, explanation).
        3. reading: title, content (250-400 words), word_count, 5 comprehension questions.
        4. dialogue: scenario, context, 8-12 lines of dialogue (role, text, translation), 3-5 alternatives.
        
        Ensure the JSON is valid and follows the schema strictly."""

    async def generate_lesson(
        self,
        language: Literal["EN", "JP"],
        topic: Optional[str] = None,
        level: Optional[str] = None,
        interest_context: Optional[str] = None,
        user_id: str = "default_user"
    ) -> Optional[Lesson]:
        """Generate a complete lesson with Fallback and Task Tracking"""
        task_id = str(uuid4())
        start_time = time.time()
        
        # 1. Determine level and topic
        if not level:
            progress = db.get_progress(user_id)
            if progress:
                level = progress['english_progress']['current_level'] if language == "EN" else progress['japanese_progress']['current_level']
            else:
                level = "A1" if language == "EN" else "N5"
        
        if not topic:
            topic = random.choice(self.ENGLISH_TOPICS if language == "EN" else self.JAPANESE_TOPICS)

        # 2. Smart Model Selection
        context_len = len(interest_context) if interest_context else 0
        model = self._select_smart_model(language, level, context_len)
        
        # Initial task status
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "running",
            "model_used": model,
            "created_at": datetime.now().isoformat()
        }
        db.save_generation_task(task_data)

        # 3. Generation with Fallback
        try:
            lesson = await self._perform_generation(language, topic, level, interest_context, model)
            
            # Success
            task_data["status"] = "success"
            task_data["duration_ms"] = int((time.time() - start_time) * 1000)
            db.save_generation_task(task_data)
            return lesson
            
        except Exception as e:
            print(f"Primary generation failed: {e}. Attempting fallback...")
            task_data["status"] = "retried"
            task_data["retry_count"] = 1
            db.save_generation_task(task_data)
            
            try:
                # Fallback to small model
                fallback_model = settings.small_model_name
                task_data["model_used"] = f"{fallback_model} (fallback)"
                lesson = await self._perform_generation(language, topic, level, interest_context, fallback_model)
                
                task_data["status"] = "success"
                task_data["duration_ms"] = int((time.time() - start_time) * 1000)
                db.save_generation_task(task_data)
                return lesson
            except Exception as fe:
                # Final Fallback: Rule-based "Safe Version"
                print(f"Fallback failed: {fe}. Using safe template.")
                task_data["status"] = "failed"
                task_data["error_message"] = str(fe)
                db.save_generation_task(task_data)
                return self._get_safe_lesson_template(language, level, topic)

    async def _perform_generation(self, language, topic, level, interest_context, model) -> Lesson:
        """Internal generation logic (P1 Fix: Removed circular import)"""
        from rag_manager import rag_manager
        
        # RAG Context
        query_text = f"{topic} {level}"
        if interest_context:
            query_text += f" {interest_context}"
        context_materials = rag_manager.query_materials(query_text, n_results=3)
        context_str = "\n".join(context_materials) if context_materials else ""
        
        # Build prompt
        system_prompt = self._get_system_prompt(language)
        if language == "EN":
            user_prompt = self._build_english_prompt(level, topic)
        else:
            user_prompt = self._build_japanese_prompt(level, topic)
            
        if context_str:
            user_prompt += f"\n\nContext:\n{context_str}"
        if interest_context:
            user_prompt += f"\n\nUser Interest: {interest_context}"

        response = self.ollama.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            format="json",
            model=model
        )
        
        if not response['success']:
            raise Exception(response.get('error', 'Ollama generation failed'))
        
        lesson_content = self.ollama.parse_json_response(response['response'])
        if not lesson_content:
            raise Exception("Failed to parse JSON response")
        
        # Normalize correct answers to text format
        self._normalize_correct_answers(lesson_content)
        
        # Create metadata
        metadata = LessonMetadata(
            lesson_id=str(uuid4()),
            language=language,
            level=level,
            topic=topic,
            generated_at=datetime.now(),
            estimated_duration_minutes=45,
            key_points=[f"Topic: {topic}", f"Level: {level}"]
        )
        
        # Interleave old content
        self._interleave_old_content(lesson_content, language)

        full_lesson = {
            "metadata": metadata.model_dump(mode='json'),
            **lesson_content
        }
        
        # Save
        file_path = self._save_lesson_file(full_lesson)
        db.save_lesson(full_lesson, file_path)
        
        return Lesson(**full_lesson)

    def _normalize_correct_answers(self, lesson_content: Dict[str, Any]):
        """Convert correct_answer from index to text for option-based exercises"""
        # Normalize grammar exercises
        if 'grammar' in lesson_content and 'exercises' in lesson_content['grammar']:
            for exercise in lesson_content['grammar']['exercises']:
                if 'options' in exercise and exercise['options'] and 'correct_answer' in exercise:
                    try:
                        index = int(exercise['correct_answer'])
                        if 0 <= index < len(exercise['options']):
                            exercise['correct_answer'] = exercise['options'][index]
                    except (ValueError, TypeError):
                        pass  # Keep as is if not a valid index
        
        # Normalize reading questions
        if 'reading' in lesson_content and 'questions' in lesson_content['reading']:
            for question in lesson_content['reading']['questions']:
                if 'options' in question and question['options'] and 'correct_answer' in question:
                    try:
                        index = int(question['correct_answer'])
                        if 0 <= index < len(question['options']):
                            question['correct_answer'] = question['options'][index]
                    except (ValueError, TypeError):
                        pass  # Keep as is if not a valid index

    def _interleave_old_content(self, lesson_content: Dict[str, Any], language: str):
        """Insert 20% content from past lessons"""
        try:
            old_lessons_meta = db.query_lessons(language=language, limit=5)
            if len(old_lessons_meta) < 2: return
            target_meta = random.choice(old_lessons_meta)
            with open(target_meta['file_path'], 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            if 'vocabulary' in old_data and len(old_data['vocabulary']) >= 2:
                old_vocab = random.sample(old_data['vocabulary'], 2)
                lesson_content['vocabulary'].extend(old_vocab)
        except: pass

    def _save_lesson_file(self, lesson_data: Dict[str, Any]) -> str:
        metadata = lesson_data['metadata']
        date_str = datetime.fromisoformat(metadata['generated_at']).strftime('%Y-%m-%d')
        lesson_dir = f"../data/lessons/{date_str}"
        os.makedirs(lesson_dir, exist_ok=True)
        file_path = f"{lesson_dir}/lesson_{metadata['lesson_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(lesson_data, f, ensure_ascii=False, indent=2)
        return file_path

    def _get_safe_lesson_template(self, language, level, topic) -> Lesson:
        """Return a pre-defined safe lesson when AI fails completely"""
        return Lesson(
            metadata=LessonMetadata(
                language=language,
                level=level,
                topic=f"{topic} (Safe Mode)",
                estimated_duration_minutes=15,
                key_points=["System Resilience", "Stability"]
            ),
            vocabulary=[
                VocabularyItem(word="Resilience", definition_zh="韌性", example_sentence="The system showed resilience.", example_translation="系統展現了韌性。")
            ],
            grammar=GrammarSection(title="Stability", explanation="Always have a backup plan.", examples=[], exercises=[]),
            reading=ReadingSection(title="System Stability", content="Learning continues even during maintenance.", word_count=50, questions=[]),
            dialogue=DialogueSection(scenario="Support", context="Maintenance", dialogue=[], alternatives=[])
        )


# Global lesson generator instance
lesson_generator = LessonGenerator()
