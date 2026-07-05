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
    DialogueLine,
    DialogueSection,
    GrammarExample,
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
from services.learning_intelligence import build_snowball_context, sync_lesson_items
from time_utils import local_now


class LessonGenerator:
    MIN_GRAMMAR_COUNT = 3
    MIN_READING_COUNT = 3
    MIN_VOCABULARY_COUNT = 8
    MIN_SENTENCE_PATTERN_COUNT = 3
    MIN_WORD_ROOT_COUNT = 3
    MIN_DIALOGUE_LINES = 6
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

    def _build_prompt(
        self,
        language: Literal["EN", "JP"],
        level: str,
        topic: str,
        snowball_context: dict[str, Any] | None = None,
    ) -> str:
        exercise_schema = (
            f"Return at least {self.MIN_GRAMMAR_COUNT} grammar exercises and "
            f"at least {self.MIN_READING_COUNT} reading comprehension questions. "
            f"Every multiple-choice item must have exactly {self.FIXED_CHOICE_COUNT} choices. "
            "The correct_answer must be one of the choices."
        )
        required_keys = (
            "objectives, vocabulary, word_roots, sentence_patterns, grammar, dialogue, "
            "reading, immersion, feynman_prompt, review_plan"
        )
        shared_schema = (
            f"Output a complete JSON object with keys: {required_keys}. "
            "Do not include markdown or explanatory prose. "
            "objectives: array of at least 3 strings. "
            "Vocabulary item fields: word, reading or phonetic, definition_zh, example_sentence, "
            "example_translation, part_of_speech, root, prefix, suffix, word_family, memory_tip, category, tags. "
            "word_roots item fields: root, meaning_zh, examples, memory_tip. "
            "sentence_patterns item fields: pattern, meaning_zh, usage_note, examples; each example has sentence and translation. "
            "Grammar fields: title, explanation, examples, exercises. "
            "Reading fields: title, content, word_count, questions. "
            "Dialogue fields: scenario, context, dialogue, alternatives. "
            "immersion fields: shadowing_text, repeat_chunks, listening_tips. "
            "feynman_prompt fields: prompt, checklist. "
            "review_plan fields: today, next_1_day, next_3_days, next_7_days. "
        )
        if language == "EN":
            prompt = (
                f"Generate an English lesson for CEFR {level} about '{topic}'. "
                f"Requested language enum is EN and requested difficulty value is {level}. "
                "Make it feel like a complete English textbook unit, not a thin worksheet. "
                f"{shared_schema}"
                f"Vocabulary must contain at least {self.MIN_VOCABULARY_COUNT} items. "
                f"sentence_patterns must contain at least {self.MIN_SENTENCE_PATTERN_COUNT} items. "
                f"word_roots must contain at least {self.MIN_WORD_ROOT_COUNT} roots, prefixes, or suffixes. "
                f"dialogue.dialogue must contain at least {self.MIN_DIALOGUE_LINES} lines. "
                "reading.content must be at least 80 words for A1/A2 and at least 120 words for B1 or higher. "
                f"{exercise_schema} "
                "Use CEFR-appropriate English content and keep every required field non-empty."
            )
        else:
            prompt = (
            f"Generate a Japanese lesson for JLPT {level} about '{topic}'. "
            f"Requested language enum is JP and requested difficulty value is {level}. "
            "Make it feel like a complete Japanese textbook unit adapted to the JLPT level. "
            f"{shared_schema}"
            f"Vocabulary must contain at least {self.MIN_VOCABULARY_COUNT} items. "
            f"sentence_patterns must contain at least {self.MIN_SENTENCE_PATTERN_COUNT} Japanese sentence patterns. "
            f"word_roots must contain at least {self.MIN_WORD_ROOT_COUNT} kanji parts, prefixes, suffixes, or word-building patterns. "
            f"dialogue.dialogue must contain at least {self.MIN_DIALOGUE_LINES} lines. "
            "reading.content must contain at least 8 Japanese sentences. "
            f"{exercise_schema} "
            "Use JLPT-appropriate Japanese content and keep every required field non-empty."
            )

        if snowball_context and any(snowball_context.get(key) for key in (
            "weak_vocabulary",
            "weak_grammar",
            "recent_vocabulary",
            "recent_sentence_patterns",
        )):
            prompt += (
                " Reuse prior learning naturally with this ratio: 70% new content, 20% recent learned items, "
                "10% weak items. Reuse weak items in dialogue, reading, and exercises without overstuffing the lesson. "
                "Mark reused items in review_plan. Snowball context: "
                f"{json.dumps(snowball_context, ensure_ascii=False)}"
            )
        return prompt

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
        snowball_context = build_snowball_context(uid, language, level)
        db.save_generation_task(
            {
                "task_id": task_id,
                "user_id": uid,
                "status": "running",
                "model_used": model,
                "created_at": local_now().isoformat(),
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
                snowball_context=snowball_context,
            )
            db.save_generation_task(
                {
                    "task_id": task_id,
                    "user_id": uid,
                    "status": "success",
                    "model_used": model,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "created_at": local_now().isoformat(),
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
                        "created_at": local_now().isoformat(),
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
                        "created_at": local_now().isoformat(),
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
        snowball_context: dict[str, Any] | None = None,
    ) -> Lesson:
        uid = user_id or settings.default_user_id
        prompt = self._build_prompt(language, level, topic, snowball_context=snowball_context)
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
        self._attach_related_item_refs(content)
        self._validate_generated_content(content)
        metadata = LessonMetadata(
            lesson_id=str(uuid4()),
            language=language,
            level=level,
            topic=topic,
            generated_at=local_now(),
            estimated_duration_minutes=45,
            key_points=[f"Topic: {topic}", f"Level: {level}"],
        )

        full_lesson: dict[str, Any] = {"metadata": metadata.model_dump(mode="json"), **content}
        if rag_evidence:
            full_lesson["evidence"] = rag_evidence

        lesson = Lesson(**full_lesson)
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path), user_id=uid)
        sync_lesson_items(user_id=uid, lesson_data=lesson.model_dump(mode="json"))
        return lesson

    def _normalize(self, content: dict[str, Any]) -> None:
        content.setdefault("objectives", [])
        content.setdefault("vocabulary", [])
        content.setdefault("word_roots", [])
        content.setdefault("sentence_patterns", [])
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
        content.setdefault(
            "immersion",
            {"shadowing_text": [], "repeat_chunks": [], "listening_tips": []},
        )
        content.setdefault("feynman_prompt", {"prompt": "", "checklist": []})
        content.setdefault(
            "review_plan",
            {"today": [], "next_1_day": [], "next_3_days": [], "next_7_days": []},
        )

        if not isinstance(content.get("objectives"), list):
            content["objectives"] = []
        if not isinstance(content.get("vocabulary"), list):
            content["vocabulary"] = []
        if not isinstance(content.get("word_roots"), list):
            content["word_roots"] = []
        if not isinstance(content.get("sentence_patterns"), list):
            content["sentence_patterns"] = []

        dialogue = content.get("dialogue")
        if isinstance(dialogue, dict):
            dialogue.setdefault("scenario", "Conversation")
            dialogue.setdefault("context", "Practice")
            dialogue.setdefault("dialogue", [])
            dialogue.setdefault("alternatives", [])
        else:
            content["dialogue"] = {
                "scenario": "Conversation",
                "context": "Practice",
                "dialogue": [],
                "alternatives": [],
            }

        immersion = content.get("immersion")
        if isinstance(immersion, dict):
            immersion.setdefault("shadowing_text", [])
            immersion.setdefault("repeat_chunks", [])
            immersion.setdefault("listening_tips", [])
        else:
            content["immersion"] = {"shadowing_text": [], "repeat_chunks": [], "listening_tips": []}

        feynman_prompt = content.get("feynman_prompt")
        if isinstance(feynman_prompt, dict):
            feynman_prompt.setdefault("prompt", "")
            feynman_prompt.setdefault("checklist", [])
        else:
            content["feynman_prompt"] = {"prompt": "", "checklist": []}

        review_plan = content.get("review_plan")
        if isinstance(review_plan, dict):
            review_plan.setdefault("today", [])
            review_plan.setdefault("next_1_day", [])
            review_plan.setdefault("next_3_days", [])
            review_plan.setdefault("next_7_days", [])
        else:
            content["review_plan"] = {"today": [], "next_1_day": [], "next_3_days": [], "next_7_days": []}

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
        dialogue = content.get("dialogue", {})
        grammar_exercises = grammar.get("exercises", []) if isinstance(grammar, dict) else []
        reading_questions = reading.get("questions", []) if isinstance(reading, dict) else []
        vocabulary = content.get("vocabulary", [])
        objectives = content.get("objectives", [])
        word_roots = content.get("word_roots", [])
        sentence_patterns = content.get("sentence_patterns", [])
        dialogue_lines = dialogue.get("dialogue", []) if isinstance(dialogue, dict) else []

        if len(objectives) < 3:
            raise RuntimeError("generated lesson must contain at least three objectives")
        if len(vocabulary) < self.MIN_VOCABULARY_COUNT:
            raise RuntimeError("generated lesson must contain at least eight vocabulary items")
        if len(word_roots) < self.MIN_WORD_ROOT_COUNT:
            raise RuntimeError("generated lesson must contain at least three word roots")
        if len(sentence_patterns) < self.MIN_SENTENCE_PATTERN_COUNT:
            raise RuntimeError("generated lesson must contain at least three sentence patterns")
        if len(dialogue_lines) < self.MIN_DIALOGUE_LINES:
            raise RuntimeError("generated lesson must contain at least six dialogue lines")
        if len(grammar_exercises) < self.MIN_GRAMMAR_COUNT:
            raise RuntimeError("generated lesson must contain at least three grammar exercises")
        if len(reading_questions) < self.MIN_READING_COUNT:
            raise RuntimeError("generated lesson must contain at least three reading questions")

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

    def _attach_related_item_refs(self, content: dict[str, Any]) -> None:
        vocabulary = [
            str(item.get("word", "")).strip()
            for item in content.get("vocabulary", [])
            if isinstance(item, dict) and str(item.get("word", "")).strip()
        ]
        grammar_title = str(content.get("grammar", {}).get("title", "")).strip()
        patterns = [
            str(item.get("pattern", "")).strip()
            for item in content.get("sentence_patterns", [])
            if isinstance(item, dict) and str(item.get("pattern", "")).strip()
        ]

        def infer_refs(text: str) -> tuple[list[str], list[str], list[str]]:
            normalized = text.lower()
            related_vocab = [word for word in vocabulary if word.lower() in normalized][:3]
            related_grammar = [grammar_title] if grammar_title and grammar_title.lower() in normalized else []
            related_patterns = [pattern for pattern in patterns if pattern.lower() in normalized][:2]
            return related_vocab, related_grammar, related_patterns

        grammar = content.get("grammar", {})
        if isinstance(grammar, dict):
            for exercise in grammar.get("exercises", []) or []:
                if not isinstance(exercise, dict):
                    continue
                related_vocab, related_grammar, related_patterns = infer_refs(
                    " ".join(
                        str(exercise.get(key, ""))
                        for key in ("question", "correct_answer", "explanation")
                    )
                )
                exercise.setdefault("related_vocabulary", related_vocab)
                exercise.setdefault("related_grammar", related_grammar or ([grammar_title] if grammar_title else []))
                exercise.setdefault("related_sentence_patterns", related_patterns)

        reading = content.get("reading", {})
        reading_context = ""
        if isinstance(reading, dict):
            reading_context = " ".join(
                [
                    str(reading.get("title", "")),
                    str(reading.get("content", "")),
                ]
            )
            for question in reading.get("questions", []) or []:
                if not isinstance(question, dict):
                    continue
                related_vocab, related_grammar, related_patterns = infer_refs(
                    reading_context
                    + " "
                    + " ".join(
                        str(question.get(key, ""))
                        for key in ("question", "correct_answer", "explanation")
                    )
                )
                question.setdefault("related_vocabulary", related_vocab)
                question.setdefault("related_grammar", related_grammar)
                question.setdefault("related_sentence_patterns", related_patterns)

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
            reading = (
                "A useful English routine can be small and steady. First, choose one real situation, such as asking for help or planning a trip. "
                "Then read the target words and say one example sentence for each word. After that, practice three sentence patterns aloud. "
                "When a sentence feels difficult, repeat a short chunk instead of forcing the whole paragraph. Next, listen to the dialogue and shadow two lines slowly. "
                "Finally, explain the lesson in your own words. This shows whether you can connect the vocabulary, grammar, reading, and speaking task. "
                "Tomorrow, review the same words before you add new ones."
            )
            data: dict[str, Any] = {
                "objectives": [
                    f"Use key words about {topic} in complete sentences.",
                    "Recognize three reusable sentence patterns.",
                    "Explain the reading and dialogue in your own words.",
                ],
                "vocabulary": [
                    VocabularyItem(word="resilience", phonetic="/rɪˈzɪl.jəns/", definition_zh="韌性", example_sentence="Consistency builds resilience.", example_translation="持續練習會建立韌性。", part_of_speech="noun", prefix="re-", word_family=["resilience", "resilient"], memory_tip="Connect resilience with coming back after a hard sentence.", category="mindset", tags=["fallback", "mindset"]),
                    VocabularyItem(word="routine", phonetic="/ruːˈtiːn/", definition_zh="例行習慣", example_sentence="A short routine helps me study.", example_translation="一個短例行習慣幫助我學習。", part_of_speech="noun", root=None, word_family=["routine", "routines"], memory_tip="Connect routine with one fixed study time.", category="study", tags=["fallback", "study"]),
                    VocabularyItem(word="review", phonetic="/rɪˈvjuː/", definition_zh="複習", example_sentence="I review new words after class.", example_translation="我下課後複習新單字。", part_of_speech="verb", prefix="re-", word_family=["review", "reviewer"], memory_tip="re- can mean again: view again.", category="study", tags=["fallback", "review"]),
                    VocabularyItem(word="confidence", phonetic="/ˈkɑːn.fə.dəns/", definition_zh="信心", example_sentence="Small wins give me confidence.", example_translation="小成功帶給我信心。", part_of_speech="noun", prefix="con-", word_family=["confident", "confidence"], memory_tip="Think of ideas coming together inside you.", category="mindset", tags=["fallback", "mindset"]),
                    VocabularyItem(word="practice", phonetic="/ˈpræk.tɪs/", definition_zh="練習", example_sentence="Practice makes the pattern familiar.", example_translation="練習讓句型變熟悉。", part_of_speech="noun", word_family=["practice", "practices"], memory_tip="Picture repeating one useful sentence.", category="study", tags=["fallback", "practice"]),
                    VocabularyItem(word="explain", phonetic="/ɪkˈspleɪn/", definition_zh="解釋", example_sentence="I can explain the lesson in my own words.", example_translation="我可以用自己的話解釋這課。", part_of_speech="verb", prefix="ex-", word_family=["explain", "explanation"], memory_tip="ex- can point outward: bring the idea out.", category="output", tags=["fallback", "output"]),
                    VocabularyItem(word="repeat", phonetic="/rɪˈpiːt/", definition_zh="重複", example_sentence="Repeat the sentence three times.", example_translation="把句子重複三次。", part_of_speech="verb", prefix="re-", word_family=["repeat", "repetition"], memory_tip="re- again plus a spoken beat.", category="shadowing", tags=["fallback", "shadowing"]),
                    VocabularyItem(word="connect", phonetic="/kəˈnekt/", definition_zh="連結", example_sentence="Connect the word to a real memory.", example_translation="把單字連結到真實記憶。", part_of_speech="verb", prefix="con-", word_family=["connect", "connection"], memory_tip="Think of two ideas joined by a line.", category="memory", tags=["fallback", "memory"]),
                    VocabularyItem(word="chunk", phonetic="/tʃʌŋk/", definition_zh="語塊", example_sentence="Learn one useful chunk at a time.", example_translation="一次學一個有用語塊。", part_of_speech="noun", word_family=["chunk", "chunks"], memory_tip="A chunk is a small piece you can repeat.", category="speaking", tags=["fallback", "speaking"]),
                ],
                "word_roots": [
                    {"root": "re-", "meaning_zh": "再次、重新", "examples": ["review", "repeat", "return"], "memory_tip": "When you see re-, look for the idea of again."},
                    {"root": "con-/com-", "meaning_zh": "一起、共同", "examples": ["connect", "confidence", "combine"], "memory_tip": "Imagine ideas coming together."},
                    {"root": "-tion", "meaning_zh": "常見名詞字尾", "examples": ["connection", "repetition", "explanation"], "memory_tip": "When a word ends in -tion, expect a noun."},
                ],
                "sentence_patterns": [
                    {"pattern": "First, ..., then ...", "meaning_zh": "首先……，然後……", "usage_note": "Use this to explain a sequence.", "examples": [{"sentence": "First, review the words, then read the passage.", "translation": "首先複習單字，然後閱讀文章。"}]},
                    {"pattern": "When ..., ...", "meaning_zh": "當……時，就……", "usage_note": "Use this to connect a situation and an action.", "examples": [{"sentence": "When a sentence is hard, I repeat one chunk.", "translation": "當句子很難時，我重複一個語塊。"}]},
                    {"pattern": "This shows whether ...", "meaning_zh": "這能顯示是否……", "usage_note": "Use this to describe the purpose of a check.", "examples": [{"sentence": "This shows whether I understand the lesson.", "translation": "這能顯示我是否理解這課。"}]},
                ],
                "grammar": GrammarSection(
                    title="Simple Present for Study Habits",
                    explanation="Use the simple present to describe habits, routines, and repeated actions.",
                    examples=[
                        GrammarExample(sentence="I review new words every day.", translation="我每天複習新單字。"),
                        GrammarExample(sentence="She practices one pattern after class.", translation="她下課後練習一個句型。"),
                    ],
                    exercises=[
                        GrammarExercise(question="Choose the sentence for a daily habit.", options=["I review words every day.", "I reviewing words every day.", "I reviewed words tomorrow."], correct_answer="I review words every day.", explanation="Simple present uses the base verb for I/you/we/they."),
                        GrammarExercise(question="Choose the best verb form: She ___ one sentence aloud.", options=["repeats", "repeat", "repeating"], correct_answer="repeats", explanation="Use -s with she/he/it in the simple present."),
                        GrammarExercise(question="Which sentence explains a routine?", options=["We practice after breakfast.", "We practiced next week.", "We are practice yesterday."], correct_answer="We practice after breakfast.", explanation="This sentence describes a repeated routine."),
                    ],
                ),
                "dialogue": DialogueSection(
                    scenario="Planning a daily study routine",
                    context="Two classmates talk after English class.",
                    dialogue=[
                        DialogueLine(speaker="Mia", text="I want to remember today's words.", translation="我想記住今天的單字。"),
                        DialogueLine(speaker="Ken", text="Start with a short review tonight.", translation="今晚先做短短的複習。"),
                        DialogueLine(speaker="Mia", text="Should I read the whole lesson again?", translation="我應該把整課再讀一次嗎？"),
                        DialogueLine(speaker="Ken", text="No, repeat three useful chunks first.", translation="不用，先重複三個有用語塊。"),
                        DialogueLine(speaker="Mia", text="Then I can explain the lesson in my own words.", translation="然後我可以用自己的話解釋這課。"),
                        DialogueLine(speaker="Ken", text="Exactly. That makes review easier tomorrow.", translation="沒錯。這會讓明天的複習更容易。"),
                    ],
                    alternatives=[],
                ),
                "reading": ReadingSection(
                    title="A Small Routine That Works",
                    content=reading,
                    word_count=len(reading.split()),
                    questions=[
                        ReadingQuestion(question="What is the main idea?", options=["Small daily practice can build learning habits.", "Only long study sessions work.", "New words should not be reviewed."], correct_answer="Small daily practice can build learning habits.", explanation="The reading emphasizes short, steady practice."),
                        ReadingQuestion(question="What should you do when a sentence feels difficult?", options=["Repeat one useful chunk slowly.", "Skip every hard sentence.", "Read faster."], correct_answer="Repeat one useful chunk slowly.", explanation="The passage recommends slowing down and repeating a chunk."),
                        ReadingQuestion(question="Why explain the lesson in your own words?", options=["To check real understanding.", "To avoid vocabulary.", "To replace all grammar practice."], correct_answer="To check real understanding.", explanation="Explaining shows whether you understand the lesson."),
                    ],
                ),
                "immersion": {"shadowing_text": [{"speaker": "Coach", "text": "I review new words every day.", "translation": "我每天複習新單字。"}, {"speaker": "Coach", "text": "When a sentence is hard, I repeat one chunk.", "translation": "當句子很難時，我重複一個語塊。"}], "repeat_chunks": ["start with a short review", "repeat three useful chunks", "in my own words"], "listening_tips": ["Listen once for meaning.", "Shadow slowly before natural speed.", "Mark words that connect ideas."]},
                "feynman_prompt": {"prompt": "Explain how a small study routine helps you remember English words.", "checklist": ["Use at least three vocabulary words.", "Use one sentence pattern.", "Give one personal example."]},
            }
        else:
            reading = "毎日、短い復習をします。まず、新しい言葉を声に出して読みます。次に、例文を一つ作ります。それから、短い会話を聞きます。難しい文は、全部ではなく短い部分で練習します。最後に、今日の内容を自分の言葉で説明します。この方法は、言葉と文法をつなげます。明日は、同じ言葉をもう一度復習します。"
            data = {
                "objectives": [f"{topic}について基本表現を使う。", "三つの文型を会話で使う。", "読解と会話の内容を自分の言葉で説明する。"],
                "vocabulary": [
                    VocabularyItem(word="復習", reading="ふくしゅう", definition_zh="複習", example_sentence="毎日、復習します。", example_translation="每天複習。", part_of_speech="名詞/動詞", root="復", word_family=["復習"], memory_tip="復表示再一次。", category="study", tags=["fallback", "study"]),
                    VocabularyItem(word="練習", reading="れんしゅう", definition_zh="練習", example_sentence="文を三回練習します。", example_translation="把句子練習三次。", part_of_speech="名詞/動詞", root="習", word_family=["練習"], memory_tip="習和學習、反覆有關。", category="study", tags=["fallback", "practice"]),
                    VocabularyItem(word="説明", reading="せつめい", definition_zh="說明、解釋", example_sentence="内容を説明します。", example_translation="說明內容。", part_of_speech="名詞/動詞", root="明", word_family=["説明"], memory_tip="明表示讓事情變清楚。", category="output", tags=["fallback", "output"]),
                    VocabularyItem(word="会話", reading="かいわ", definition_zh="會話", example_sentence="会話を聞きます。", example_translation="聽會話。", part_of_speech="名詞", root="話", word_family=["会話"], memory_tip="話和說話有關。", category="dialogue", tags=["fallback", "dialogue"]),
                    VocabularyItem(word="短い", reading="みじかい", definition_zh="短的", example_sentence="短い文を読みます。", example_translation="閱讀短句。", part_of_speech="形容詞", word_family=["短い"], memory_tip="短和長相反。", category="reading", tags=["fallback", "reading"]),
                    VocabularyItem(word="言葉", reading="ことば", definition_zh="語言、詞語", example_sentence="新しい言葉を覚えます。", example_translation="記住新的詞語。", part_of_speech="名詞", root="言", word_family=["言葉"], memory_tip="言和說話、語言有關。", category="vocabulary", tags=["fallback", "vocabulary"]),
                    VocabularyItem(word="聞く", reading="きく", definition_zh="聽", example_sentence="音声を聞きます。", example_translation="聽音檔。", part_of_speech="動詞", root="聞", word_family=["聞く"], memory_tip="門裡有耳，表示聽。", category="listening", tags=["fallback", "listening"]),
                    VocabularyItem(word="自分", reading="じぶん", definition_zh="自己", example_sentence="自分の言葉で話します。", example_translation="用自己的話說。", part_of_speech="名詞", root="自", word_family=["自分"], memory_tip="自表示自己。", category="speaking", tags=["fallback", "speaking"]),
                ],
                "word_roots": [
                    {"root": "復", "meaning_zh": "再次、回復", "examples": ["復習", "復活", "回復"], "memory_tip": "看到復，想成再做一次。"},
                    {"root": "習", "meaning_zh": "學習、反覆練", "examples": ["練習", "学習", "習う"], "memory_tip": "習常和學、練有關。"},
                    {"root": "話", "meaning_zh": "說話、故事", "examples": ["会話", "電話", "話す"], "memory_tip": "話和口語溝通連在一起。"},
                ],
                "sentence_patterns": [
                    {"pattern": "まず、...ます。次に、...ます。", "meaning_zh": "首先……。接著……。", "usage_note": "用來排列學習步驟。", "examples": [{"sentence": "まず、言葉を読みます。次に、文を作ります。", "translation": "首先讀詞語。接著造句。"}]},
                    {"pattern": "...ではなく、...ます。", "meaning_zh": "不是……，而是……。", "usage_note": "用來修正方法或選擇。", "examples": [{"sentence": "全部ではなく、短い部分を練習します。", "translation": "不是全部，而是練習短的部分。"}]},
                    {"pattern": "...と...をつなげます。", "meaning_zh": "把……和……連起來。", "usage_note": "用來說明兩個學習內容的連結。", "examples": [{"sentence": "言葉と文法をつなげます。", "translation": "把詞語和文法連起來。"}]},
                ],
                "grammar": GrammarSection(
                    title="ます形で学習習慣を話す",
                    explanation="ます形は丁寧に行動や習慣を言う時に使います。",
                    examples=[
                        GrammarExample(sentence="毎日、復習します。", translation="每天複習。"),
                        GrammarExample(sentence="短い文を読みます。", translation="閱讀短句。"),
                    ],
                    exercises=[
                        GrammarExercise(question="正しい文を選んでください。", options=["毎日、復習します。", "毎日、復習ですます。", "毎日、復習を。"], correct_answer="毎日、復習します。", explanation="動作はます形で言います。"),
                        GrammarExercise(question="「聞く」のます形はどれですか。", options=["聞きます", "聞くます", "聞いてます"], correct_answer="聞きます", explanation="聞くは聞きますになります。"),
                        GrammarExercise(question="順番を表す言葉はどれですか。", options=["まず", "とても", "大きい"], correct_answer="まず", explanation="まずは最初の手順を表します。"),
                    ],
                ),
                "dialogue": DialogueSection(
                    scenario="短い復習の計画",
                    context="二人の学習者が授業の後で話します。",
                    dialogue=[
                        DialogueLine(speaker="ミア", text="今日の言葉を覚えたいです。", translation="我想記住今天的詞語。"),
                        DialogueLine(speaker="ケン", text="まず、短い復習をしましょう。", translation="首先做短短的複習吧。"),
                        DialogueLine(speaker="ミア", text="全部をもう一度読みますか。", translation="要把全部再讀一次嗎？"),
                        DialogueLine(speaker="ケン", text="全部ではなく、短い部分を練習します。", translation="不是全部，而是練習短的部分。"),
                        DialogueLine(speaker="ミア", text="それから、自分の言葉で説明します。", translation="然後用自己的話說明。"),
                        DialogueLine(speaker="ケン", text="いいですね。明日も復習できます。", translation="很好。明天也可以複習。"),
                    ],
                    alternatives=[],
                ),
                "reading": ReadingSection(
                    title="短い復習",
                    content=reading,
                    word_count=len(reading.split()),
                    questions=[
                        ReadingQuestion(question="読み物の主な考えは何ですか。", options=["短い復習は続けやすいです。", "復習は必要ありません。", "単語だけを書きます。"], correct_answer="短い復習は続けやすいです。", explanation="文章は小さい習慣の大切さを説明しています。"),
                        ReadingQuestion(question="難しい文はどうしますか。", options=["短い部分を練習します。", "すぐ全部やめます。", "早く読みます。"], correct_answer="短い部分を練習します。", explanation="全部ではなく短い部分を練習すると書いてあります。"),
                        ReadingQuestion(question="最後に何をしますか。", options=["自分の言葉で説明します。", "新しい本を買います。", "音声を消します。"], correct_answer="自分の言葉で説明します。", explanation="最後に内容を自分の言葉で説明します。"),
                    ],
                ),
                "immersion": {"shadowing_text": [{"speaker": "コーチ", "text": "毎日、短い復習をします。", "translation": "每天做短短的複習。"}, {"speaker": "コーチ", "text": "自分の言葉で説明します。", "translation": "用自己的話說明。"}], "repeat_chunks": ["短い復習をします", "全部ではなく", "自分の言葉で"], "listening_tips": ["一回目は意味を聞きます。", "二回目は短い部分をまねします。", "助詞を意識します。"]},
                "feynman_prompt": {"prompt": "短い復習の方法を自分の言葉で説明してください。", "checklist": ["三つの言葉を使う。", "一つの文型を使う。", "自分の例を一つ言う。"]},
            }

        data["review_plan"] = {
            "today": ["Read the dialogue aloud.", "Answer all grammar and reading questions."],
            "next_1_day": ["Review the eight vocabulary words.", "Repeat the three chunks."],
            "next_3_days": ["Write three new examples.", "Explain the reading from memory."],
            "next_7_days": ["Retake the questions.", "Move difficult words into focused review."],
        }
        lesson = Lesson(
            metadata=LessonMetadata(
                language=language,
                level=level,
                topic=f"{topic} (Fallback)",
                estimated_duration_minutes=35,
                key_points=["Fallback textbook unit", "Core practice", "Review plan"],
            ),
            **data,
        )
        file_path = self._save_lesson_file(lesson.model_dump(mode="json"))
        db.save_lesson(lesson.model_dump(mode="json"), str(file_path), user_id=user_id)
        sync_lesson_items(user_id=user_id, lesson_data=lesson.model_dump(mode="json"))
        return lesson


lesson_generator = LessonGenerator()
