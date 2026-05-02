"""Lesson generator using Ollama AI with deterministic fallback content."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from config import settings
from database import db
from models import DialogueSection, GrammarSection, Lesson, LessonMetadata, ReadingSection, VocabularyItem
from ollama_client import ollama_client
from rag_manager import rag_manager


class LessonGenerator:
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
        return "You are an English tutor. Return valid JSON only." if language == "EN" else "You are a Japanese tutor. Return valid JSON only."

    def _build_prompt(self, language: Literal["EN", "JP"], level: str, topic: str) -> str:
        if language == "EN":
            return (
                f"Generate an English lesson for CEFR {level} about '{topic}'. "
                "Return JSON with keys: vocabulary, grammar, reading, dialogue. "
                "Vocabulary item fields: word, phonetic, definition_zh, example_sentence, example_translation."
            )
        return (
            f"Generate a Japanese lesson for JLPT {level} about '{topic}'. "
            "Return JSON with keys: vocabulary, grammar, reading, dialogue. "
            "Vocabulary item fields: word, reading, definition_zh, example_sentence, example_translation."
        )

    def _select_model(self, language: str, level: str, context_len: int) -> str:
        if language == "JP" or level in {"C1", "C2", "N1"} or context_len > 1000:
            return settings.large_model_name
        return settings.small_model_name

    async def generate_lesson(
        self,
        language: Literal["EN", "JP"],
        topic: Optional[str] = None,
        level: Optional[str] = None,
        interest_context: Optional[str] = None,
        user_id: Optional[str] = None,
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
        interest_context: Optional[str],
        model: str,
        user_id: Optional[str] = None,
    ) -> Lesson:
        uid = user_id or settings.default_user_id
        prompt = self._build_prompt(language, level, topic)
        if interest_context:
            prompt += f" Context from user: {interest_context}"

        rag_evidence = rag_manager.query_materials(f"{topic} {level}", user_id=uid, language=language, n_results=3)
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

        content = self.ollama.parse_json_response(response["response"])
        if not content:
            raise RuntimeError("model returned non-json content")

        self._normalize(content)
        metadata = LessonMetadata(
            lesson_id=str(uuid4()),
            language=language,
            level=level,
            topic=topic,
            generated_at=datetime.now(),
            estimated_duration_minutes=45,
            key_points=[f"Topic: {topic}", f"Level: {level}"],
        )

        full_lesson: Dict[str, Any] = {"metadata": metadata.model_dump(mode="json"), **content}
        if rag_evidence:
            full_lesson["evidence"] = rag_evidence

        lesson = Lesson(**full_lesson)
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path), user_id=uid)
        return lesson

    def _normalize(self, content: Dict[str, Any]) -> None:
        content.setdefault("vocabulary", [])
        content.setdefault("grammar", {"title": "Grammar", "explanation": "", "examples": [], "exercises": []})
        content.setdefault("reading", {"title": "Reading", "content": "", "word_count": 0, "questions": []})
        content.setdefault("dialogue", {"scenario": "Conversation", "context": "Practice", "dialogue": [], "alternatives": []})

        for section in ("grammar", "reading"):
            key = "exercises" if section == "grammar" else "questions"
            for item in content.get(section, {}).get(key, []):
                options = item.get("options") or []
                answer = item.get("correct_answer")
                if isinstance(answer, int) and 0 <= answer < len(options):
                    item["correct_answer"] = options[answer]
                elif answer is None:
                    item["correct_answer"] = ""

    def _save_lesson_file(self, lesson_data: Dict[str, Any]) -> Path:
        metadata = lesson_data["metadata"]
        generated_at = datetime.fromisoformat(metadata["generated_at"])
        lesson_dir = settings.lessons_dir / generated_at.strftime("%Y-%m-%d")
        lesson_dir.mkdir(parents=True, exist_ok=True)
        file_path = lesson_dir / f"lesson_{metadata['lesson_id']}.json"
        file_path.write_text(json.dumps(lesson_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def _safe_lesson(self, language: Literal["EN", "JP"], level: str, topic: str, *, user_id: str) -> Lesson:
        vocab = (
            VocabularyItem(
                word="resilience",
                phonetic="/rɪˈzɪl.jəns/",
                definition_zh="韌性；恢復力",
                example_sentence="Consistency builds resilience.",
                example_translation="持續練習能培養韌性。",
            )
            if language == "EN"
            else VocabularyItem(
                word="習慣",
                reading="しゅうかん",
                definition_zh="習慣",
                example_sentence="毎日少しずつ勉強する習慣を作りましょう。",
                example_translation="讓我們建立每天一點點學習的習慣。",
            )
        )
        reading_content = (
            "Study a little every day to build confidence."
            if language == "EN"
            else "毎日少しずつ勉強すると、自信が少しずつ育っていきます。"
        )
        reading_answer = "Study daily" if language == "EN" else "每天少量學習"
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
                title="Simple Present" if language == "EN" else "基本形",
                explanation="Use it for habits and routines." if language == "EN" else "基本形可用來表達日常習慣與固定動作。",
                examples=[],
                exercises=[
                    {
                        "question": "Choose the correct sentence for a daily habit:" if language == "EN" else "請選出描述日常習慣的正確句子：",
                        "options": (
                            [
                                "I study a little every day.",
                                "I am study a little every day.",
                                "I studied a little every day yesterday.",
                            ]
                            if language == "EN"
                            else [
                                "私は毎日少しずつ勉強します。",
                                "私は毎日少しずつ勉強してです。",
                                "私は昨日毎日少しずつ勉強しました。",
                            ]
                        ),
                        "correct_answer": "I study a little every day." if language == "EN" else "私は毎日少しずつ勉強します。",
                        "explanation": "Use the base pattern for habits." if language == "EN" else "描述習慣時使用基本形最自然。",
                    }
                ],
            ),
            reading=ReadingSection(
                title="Short Reading",
                content=reading_content,
                word_count=len(reading_content.split()),
                questions=[
                    {
                        "question": "What is the main idea of the reading?" if language == "EN" else "這段短文的重點是什麼？",
                        "options": (
                            ["Study daily", "Never study", "Study only once a week"]
                            if language == "EN"
                            else ["每天少量學習", "完全不要學習", "每週只學一次"]
                        ),
                        "correct_answer": reading_answer,
                        "explanation": "The passage recommends steady daily practice." if language == "EN" else "這段內容強調每天穩定練習的重要性。",
                    }
                ],
            ),
            dialogue=DialogueSection(scenario="Practice", context="Daily study", dialogue=[], alternatives=[]),
        )
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path), user_id=user_id)
        return lesson


lesson_generator = LessonGenerator()
