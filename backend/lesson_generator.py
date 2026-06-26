"""Lesson generator using Ollama AI with deterministic fallback content."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from config import settings
from database import db
from models import (
    DialogueSection,
    GrammarExercise,
    GrammarSection,
    Lesson,
    LessonMetadata,
    ReadingQuestion,
    ReadingSection,
    VocabularyItem,
)
from ollama_client import ollama_client
from rag_manager import rag_manager


class LessonGenerator:
    FIXED_GRAMMAR_COUNT = 1
    FIXED_READING_COUNT = 1
    FIXED_CHOICE_COUNT = 3
    ENGLISH_TOPICS = [
        "Daily Conversation",
        "Business Communication",
        "Travel",
        "Technology",
        "Health",
        "Education",
    ]
    JAPANESE_TOPICS = [
        "Cafe Conversation",
        "Commuting",
        "Shopping",
        "Self Introduction",
        "Office Small Talk",
        "Travel Planning",
    ]

    def __init__(self) -> None:
        self.ollama = ollama_client

    def _get_system_prompt(self, language: Literal["EN", "JP"]) -> str:
        if language == "EN":
            return (
                "You are an English tutor. Output JSON only. "
                "Do not output markdown, code fences, explanations, or extra text."
            )
        return (
            "You are a Japanese tutor. Output JSON only. "
            "Do not output markdown, code fences, explanations, or extra text."
        )

    def _build_prompt(self, language: Literal["EN", "JP"], level: str, topic: str) -> str:
        exercise_schema = (
            f"Return exactly {self.FIXED_GRAMMAR_COUNT} grammar exercise and "
            f"exactly {self.FIXED_READING_COUNT} reading question. "
            f"Every multiple-choice item must have exactly {self.FIXED_CHOICE_COUNT} choices. "
            "The correct_answer must be one of the choices."
        )
        if language == "EN":
            return (
                f"Generate an English lesson for CEFR {level} about '{topic}'. "
                f"Requested language enum is EN and requested difficulty value is {level}. "
                "Output JSON only with keys: vocabulary, grammar, reading, dialogue. "
                "Do not include markdown or explanatory prose. "
                "Vocabulary item fields: word, phonetic, definition_zh, example_sentence, example_translation. "
                "Grammar fields: title, explanation, examples, exercises. "
                "Reading fields: title, content, word_count, questions. "
                "Dialogue fields: scenario, context, dialogue, alternatives. "
                f"{exercise_schema} "
                "Use CEFR-appropriate English content and keep every required field non-empty."
            )
        return (
            f"Generate a Japanese lesson for JLPT {level} about '{topic}'. "
            f"Requested language enum is JP and requested difficulty value is {level}. "
            "Output JSON only with keys: vocabulary, grammar, reading, dialogue. "
            "Do not include markdown or explanatory prose. "
            "Vocabulary item fields: word, reading, definition_zh, example_sentence, example_translation. "
            "Grammar fields: title, explanation, examples, exercises. "
            "Reading fields: title, content, word_count, questions. "
            "Dialogue fields: scenario, context, dialogue, alternatives. "
            f"{exercise_schema} "
            "Use JLPT-appropriate Japanese content and keep every required field non-empty."
        )

    def _select_model(self, language: str, level: str, context_len: int) -> str:
        if language == "JP" or level in {"C1", "C2", "N1"} or context_len > 1000:
            return settings.large_model_name
        return settings.small_model_name

    async def generate_lesson(
        self,
        language: Literal["EN", "JP"],
        topic: str | None = None,
        level: str | None = None,
        interest_context: str | None = None,
        user_id: str | None = None,
    ) -> Lesson:
        task_id = str(uuid4())
        start_time = time.time()
        uid = user_id or settings.default_user_id
        progress = db.get_progress(uid)

        if not level:
            level = (
                progress["english_progress"]["current_level"]
                if language == "EN"
                else progress["japanese_progress"]["current_level"]
            )
        if not topic:
            topic = random.choice(self.ENGLISH_TOPICS if language == "EN" else self.JAPANESE_TOPICS)

        model = self._select_model(language, level, len(interest_context or ""))
        db.save_generation_task(
            {
                "task_id": task_id,
                "user_id": uid,
                "status": "running",
                "model_used": model,
                "created_at": datetime.now().isoformat(),
            }
        )

        try:
            lesson = await self._generate_with_model(
                language=language,
                level=level,
                topic=topic,
                interest_context=interest_context,
                model=model,
                user_id=uid,
            )
            db.save_generation_task(
                {
                    "task_id": task_id,
                    "user_id": uid,
                    "status": "success",
                    "model_used": model,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "created_at": datetime.now().isoformat(),
                }
            )
            return lesson
        except Exception as err:
            try:
                fallback = self._safe_lesson(language, level, topic, user_id=uid)
                db.save_generation_task(
                    {
                        "task_id": task_id,
                        "user_id": uid,
                        "status": "fallback_success",
                        "model_used": model,
                        "error_message": str(err),
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "created_at": datetime.now().isoformat(),
                    }
                )
                return fallback
            except Exception as fallback_err:
                db.save_generation_task(
                    {
                        "task_id": task_id,
                        "user_id": uid,
                        "status": "failed",
                        "model_used": model,
                        "error_message": f"{err} | fallback_failed: {fallback_err}",
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "created_at": datetime.now().isoformat(),
                    }
                )
                raise

    async def _generate_with_model(
        self,
        language: Literal["EN", "JP"],
        level: str,
        topic: str,
        interest_context: str | None,
        model: str,
        user_id: str | None = None,
    ) -> Lesson:
        uid = user_id or settings.default_user_id
        prompt = self._build_prompt(language, level, topic)
        if interest_context:
            prompt += f" Context from user: {interest_context}"

        rag_evidence = rag_manager.query_materials(
            f"{topic} {level}",
            user_id=uid,
            language=language,
            n_results=3,
        )
        if rag_evidence:
            context_texts = [
                item.get("text", "")
                for item in rag_evidence
                if isinstance(item, dict) and item.get("text")
            ]
            if context_texts:
                prompt += "\n\nLearner-uploaded reference excerpts (optional; use only if relevant, do not invent facts):\n"
                prompt += "\n---\n".join(context_texts)

        response = await self.ollama.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt(language),
            model=model,
            format="json",
            timeout_profile="lesson",
        )
        if not response.get("success"):
            raise RuntimeError(response.get("error", "generation failed"))

        parsed_content = self.ollama.parse_json_response(response["response"])
        if not parsed_content:
            raise RuntimeError("model returned non-json content")

        content: dict[str, Any] = dict(parsed_content)
        self._normalize(content)
        self._validate_generated_content(content)
        metadata = LessonMetadata(
            lesson_id=str(uuid4()),
            language=language,
            level=level,
            topic=topic,
            generated_at=datetime.now(),
            estimated_duration_minutes=45,
            key_points=[f"Topic: {topic}", f"Level: {level}"],
        )

        full_lesson: dict[str, Any] = {"metadata": metadata.model_dump(mode="json"), **content}
        if rag_evidence:
            full_lesson["evidence"] = rag_evidence

        lesson = Lesson(**full_lesson)
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path), user_id=uid)
        return lesson

    def _normalize(self, content: dict[str, Any]) -> None:
        content.setdefault("vocabulary", [])
        content.setdefault(
            "grammar",
            {"title": "Grammar", "explanation": "", "examples": [], "exercises": []},
        )
        content.setdefault(
            "reading",
            {"title": "Reading", "content": "", "word_count": 0, "questions": []},
        )
        content.setdefault(
            "dialogue",
            {
                "scenario": "Conversation",
                "context": "Practice",
                "dialogue": [],
                "alternatives": [],
            },
        )

        for section in ("grammar", "reading"):
            key = "exercises" if section == "grammar" else "questions"
            section_items = content.get(section, {})
            if not isinstance(section_items, dict):
                continue
            raw_items = section_items.get(key, [])
            if not isinstance(raw_items, list):
                continue
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                options = item.get("options") or []
                answer = item.get("correct_answer")
                if isinstance(answer, int) and 0 <= answer < len(options):
                    item["correct_answer"] = options[answer]
                elif answer is None:
                    item["correct_answer"] = ""

    def _validate_generated_content(self, content: dict[str, Any]) -> None:
        grammar = content.get("grammar", {})
        reading = content.get("reading", {})
        grammar_exercises = grammar.get("exercises", []) if isinstance(grammar, dict) else []
        reading_questions = reading.get("questions", []) if isinstance(reading, dict) else []

        if len(grammar_exercises) != self.FIXED_GRAMMAR_COUNT:
            raise RuntimeError("generated lesson must contain exactly one grammar exercise")
        if len(reading_questions) != self.FIXED_READING_COUNT:
            raise RuntimeError("generated lesson must contain exactly one reading question")

        for item in list(grammar_exercises) + list(reading_questions):
            if not isinstance(item, dict):
                raise RuntimeError("generated lesson item must be an object")
            options = item.get("options")
            answer = item.get("correct_answer")
            if not isinstance(options, list) or len(options) != self.FIXED_CHOICE_COUNT:
                raise RuntimeError("generated lesson choices must contain exactly three options")
            if any(not isinstance(choice, str) or not choice.strip() for choice in options):
                raise RuntimeError("generated lesson choices must be non-empty strings")
            if not isinstance(answer, str) or answer not in options:
                raise RuntimeError("generated lesson correct_answer must match one of the choices")

    def _save_lesson_file(self, lesson_data: dict[str, Any]) -> Path:
        metadata = lesson_data["metadata"]
        generated_at = datetime.fromisoformat(metadata["generated_at"])
        lesson_dir = settings.lessons_dir / generated_at.strftime("%Y-%m-%d")
        lesson_dir.mkdir(parents=True, exist_ok=True)
        file_path = lesson_dir / f"lesson_{metadata['lesson_id']}.json"
        file_path.write_text(json.dumps(lesson_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def _safe_lesson(
        self,
        language: Literal["EN", "JP"],
        level: str,
        topic: str,
        *,
        user_id: str,
    ) -> Lesson:
        if language == "EN":
            vocab = VocabularyItem(
                word="resilience",
                phonetic="/rɪˈzɪl.jəns/",
                definition_zh="韌性",
                example_sentence="Consistency builds resilience.",
                example_translation="持續練習能建立韌性。",
            )
            reading_content = "Study a little every day to build confidence."
            grammar_title = "Simple Present"
            grammar_explanation = "Use it for habits and routines."
            grammar_exercise = GrammarExercise(
                question="Choose the correct sentence for a daily habit:",
                options=[
                    "I study a little every day.",
                    "I am study a little every day.",
                    "I studied a little every day yesterday.",
                ],
                correct_answer="I study a little every day.",
                explanation="Use the base form to describe a habit.",
            )
            reading_question = ReadingQuestion(
                question="What is the main idea of the reading?",
                options=["Study daily", "Never study", "Study only once a week"],
                correct_answer="Study daily",
                explanation="The passage recommends steady daily practice.",
            )
        else:
            vocab = VocabularyItem(
                word="継続",
                reading="けいぞく",
                definition_zh="持續，持之以恆",
                example_sentence="毎日少しずつ勉強すると力がつきます。",
                example_translation="每天一點點地學習就能累積實力。",
            )
            reading_content = "毎日少しずつ勉強すると、自信がついてきます。"
            grammar_title = "習慣を表す文"
            grammar_explanation = "習慣や日課を話すときは、基本形をよく使います。"
            grammar_exercise = GrammarExercise(
                question="毎日の習慣として自然な文を選んでください。",
                options=[
                    "私は毎日少し勉強します。",
                    "私は毎日少し勉強してです。",
                    "私は昨日毎日少し勉強します。",
                ],
                correct_answer="私は毎日少し勉強します。",
                explanation="習慣を表すときは自然な基本形を使います。",
            )
            reading_question = ReadingQuestion(
                question="本文の中心的な考えは何ですか。",
                options=[
                    "毎日勉強すること",
                    "全然勉強しないこと",
                    "週に一度だけ勉強すること",
                ],
                correct_answer="毎日勉強すること",
                explanation="本文は毎日の継続的な練習を勧めています。",
            )

        lesson = Lesson(
            metadata=LessonMetadata(
                language=language,
                level=level,
                topic=f"{topic} (Fallback)",
                estimated_duration_minutes=15,
                key_points=["Fallback lesson", "Core practice"],
            ),
            vocabulary=[vocab],
            grammar=GrammarSection(
                title=grammar_title,
                explanation=grammar_explanation,
                examples=[],
                exercises=[grammar_exercise],
            ),
            reading=ReadingSection(
                title="Short Reading",
                content=reading_content,
                word_count=len(reading_content.split()),
                questions=[reading_question],
            ),
            dialogue=DialogueSection(
                scenario="Practice",
                context="Daily study",
                dialogue=[],
                alternatives=[],
            ),
        )
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path), user_id=user_id)
        return lesson


lesson_generator = LessonGenerator()
