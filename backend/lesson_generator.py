"""Lesson generator using Ollama AI."""
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from config import settings
from database import db
from models import (
    DialogueSection,
    GrammarSection,
    Lesson,
    LessonMetadata,
    ReadingSection,
    VocabularyItem,
)
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
        "日常会話",
        "仕事",
        "旅行",
        "買い物",
        "学校生活",
        "趣味",
    ]

    def __init__(self) -> None:
        self.ollama = ollama_client

    def _get_system_prompt(self, language: Literal["EN", "JP"]) -> str:
        if language == "EN":
            return "You are an English tutor. Return valid JSON only."
        return "You are a Japanese tutor. Return valid JSON only."

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
            level = progress["english_progress"]["current_level"] if language == "EN" else progress["japanese_progress"]["current_level"]
        if not topic:
            topic = random.choice(self.ENGLISH_TOPICS if language == "EN" else self.JAPANESE_TOPICS)

        model = self._select_model(language, level, len(interest_context or ""))
        db.save_generation_task({
            "task_id": task_id,
            "user_id": uid,
            "status": "running",
            "model_used": model,
            "created_at": datetime.now().isoformat(),
        })

        try:
            lesson = await self._generate_with_model(language, level, topic, interest_context, model)
            db.save_generation_task({
                "task_id": task_id,
                "user_id": uid,
                "status": "success",
                "model_used": model,
                "duration_ms": int((time.time() - start_time) * 1000),
                "created_at": datetime.now().isoformat(),
            })
            return lesson
        except Exception as err:
            fallback = self._safe_lesson(language, level, topic)
            db.save_generation_task({
                "task_id": task_id,
                "user_id": uid,
                "status": "failed",
                "model_used": model,
                "error_message": str(err),
                "duration_ms": int((time.time() - start_time) * 1000),
                "created_at": datetime.now().isoformat(),
            })
            return fallback

    async def _generate_with_model(
        self,
        language: Literal["EN", "JP"],
        level: str,
        topic: str,
        interest_context: Optional[str],
        model: str,
    ) -> Lesson:
        prompt = self._build_prompt(language, level, topic)
        if interest_context:
            prompt += f" Context from user: {interest_context}"

        snippets = rag_manager.query_materials(
            f"{topic} {level}",
            n_results=3,
            filter_criteria={"language": language},
        )
        if snippets:
            prompt += "\n\nLearner-uploaded reference excerpts (optional; use only if relevant, do not invent facts):\n"
            prompt += "\n---\n".join(snippets[:3])

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

        full_lesson = {
            "metadata": metadata.model_dump(mode="json"),
            **content,
        }
        lesson = Lesson(**full_lesson)

        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path))
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

    def _safe_lesson(self, language: Literal["EN", "JP"], level: str, topic: str) -> Lesson:
        metadata = LessonMetadata(
            language=language,
            level=level,
            topic=f"{topic} (Fallback)",
            estimated_duration_minutes=15,
            key_points=["Fallback lesson", "Core practice"],
        )
        lesson = Lesson(
            metadata=metadata,
            vocabulary=[
                VocabularyItem(
                    word="resilience",
                    reading=None,
                    phonetic="/rɪˈzɪl.jəns/" if language == "EN" else None,
                    definition_zh="韌性",
                    example_sentence="Consistency builds resilience.",
                    example_translation="持續練習會建立韌性。",
                )
            ],
            grammar=GrammarSection(title="Simple Present", explanation="Use it for habits.", examples=[], exercises=[]),
            reading=ReadingSection(title="Short Reading", content="Study a little every day.", word_count=6, questions=[]),
            dialogue=DialogueSection(scenario="Practice", context="Daily study", dialogue=[], alternatives=[]),
        )
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path))
        return lesson


lesson_generator = LessonGenerator()
