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

    def _build_prompt(self, language: Literal["EN", "JP"], level: str, topic: str) -> str:
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
            return (
                f"Generate an English lesson for CEFR {level} about '{topic}'. "
                f"Requested language enum is EN and requested difficulty value is {level}. "
                "Make it feel like a complete English textbook unit, not a thin worksheet. "
                f"{shared_schema}"
                f"Vocabulary must contain at least {self.MIN_VOCABULARY_COUNT} items. "
                f"sentence_patterns must contain at least {self.MIN_SENTENCE_PATTERN_COUNT} items. "
                f"word_roots must contain at least {self.MIN_WORD_ROOT_COUNT} roots, prefixes, or suffixes. "
                f"dialogue.dialogue must contain at least {self.MIN_DIALOGUE_LINES} lines. "
                "reading.content must be at least 120 words; A1/A2 may be shorter, but never only one sentence. "
                f"{exercise_schema} "
                "Use CEFR-appropriate English content and keep every required field non-empty."
            )
        return (
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

    def _safe_lesson(
        self,
        language: Literal["EN", "JP"],
        level: str,
        topic: str,
        *,
        user_id: str,
    ) -> Lesson:
        if language == "EN":
            words = [
                ("resilience", "/rɪˈzɪl.jəns/", "韌性", "Consistency builds resilience.", "持續練習能建立韌性。", "noun", "re-", "mindset"),
                ("routine", "/ruːˈtiːn/", "例行習慣", "A short routine helps me study.", "短短的例行習慣幫助我學習。", "noun", "", "study"),
                ("review", "/rɪˈvjuː/", "複習", "I review new words after class.", "我下課後複習新單字。", "verb", "re-", "review"),
                ("confidence", "/ˈkɑːn.fə.dəns/", "信心", "Small wins give me confidence.", "小小的成功給我信心。", "noun", "con-", "mindset"),
                ("practice", "/ˈpræk.tɪs/", "練習", "Practice makes the pattern familiar.", "練習讓句型變熟悉。", "noun", "", "study"),
                ("explain", "/ɪkˈspleɪn/", "解釋", "I can explain the lesson in my own words.", "我可以用自己的話解釋本課。", "verb", "ex-", "output"),
                ("repeat", "/rɪˈpiːt/", "重複", "Repeat the sentence three times.", "把句子重複三次。", "verb", "re-", "shadowing"),
                ("connect", "/kəˈnekt/", "連結", "Connect the word to a real memory.", "把單字連到真實記憶。", "verb", "con-", "memory"),
            ]
            reading = (
                "A strong study habit does not need to be dramatic. It can start with ten quiet minutes each day. "
                "First, choose one small topic, such as daily routines or travel phrases. Then read a short passage and mark the words you can use today. "
                "After that, practice three sentence patterns aloud. When a sentence feels difficult, slow down and repeat one useful chunk, not the whole paragraph. "
                "Finally, explain the lesson in your own words. This simple step shows whether you truly understand the vocabulary, the grammar, and the main idea. "
                "When you return tomorrow, review the same words quickly before learning new ones."
            )
            data = {
                "objectives": [
                    f"Use key words about {topic} in complete sentences.",
                    "Recognize three reusable sentence patterns.",
                    "Explain the reading and dialogue in your own words.",
                ],
                "vocabulary": [
                    VocabularyItem(
                        word=word,
                        phonetic=phonetic,
                        definition_zh=definition,
                        example_sentence=example,
                        example_translation=translation,
                        part_of_speech=pos,
                        root=root or None,
                        word_family=[word, f"{word}s"],
                        memory_tip=f"Connect '{word}' with one personal memory.",
                        category=category,
                        tags=["fallback", category],
                    )
                    for word, phonetic, definition, example, translation, pos, root, category in words
                ],
                "word_roots": [
                    {"root": "re-", "meaning_zh": "再次、回到", "examples": ["review", "repeat", "return"], "memory_tip": "re- often points to doing something again."},
                    {"root": "con-/com-", "meaning_zh": "一起、共同", "examples": ["connect", "confidence", "combine"], "memory_tip": "Think of ideas coming together."},
                    {"root": "-tion", "meaning_zh": "名詞字尾，表示動作或狀態", "examples": ["action", "connection", "revision"], "memory_tip": "When you see -tion, expect a noun."},
                ],
                "sentence_patterns": [
                    {"pattern": "It can start with ...", "meaning_zh": "它可以從……開始", "usage_note": "Use this to make a goal manageable.", "examples": [{"sentence": "It can start with ten minutes.", "translation": "它可以從十分鐘開始。"}]},
                    {"pattern": "When ..., ...", "meaning_zh": "當……時，……", "usage_note": "Use this to connect a situation and an action.", "examples": [{"sentence": "When a word is hard, I write an example.", "translation": "當單字很難時，我寫一個例句。"}]},
                    {"pattern": "This shows whether ...", "meaning_zh": "這顯示是否……", "usage_note": "Use this to explain the purpose of a check.", "examples": [{"sentence": "This shows whether I understand the lesson.", "translation": "這顯示我是否理解本課。"}]},
                ],
                "grammar": GrammarSection(
                    title="Simple Present for Habits",
                    explanation="Use the simple present to describe routines, facts, and repeated study actions.",
                    examples=[
                        {"sentence": "I review new words every day.", "translation": "我每天複習新單字。"},
                        {"sentence": "She practices one pattern after class.", "translation": "她下課後練習一個句型。"},
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
                        {"speaker": "Mia", "text": "I want to remember today's words.", "translation": "我想記住今天的單字。"},
                        {"speaker": "Ken", "text": "Start with a short review tonight.", "translation": "今晚先做短短的複習。"},
                        {"speaker": "Mia", "text": "Should I read the whole lesson again?", "translation": "我要把整課重讀一次嗎？"},
                        {"speaker": "Ken", "text": "No, repeat three useful chunks first.", "translation": "不用，先重複三個有用片語。"},
                        {"speaker": "Mia", "text": "Then I can explain the lesson in my own words.", "translation": "然後我可以用自己的話解釋本課。"},
                        {"speaker": "Ken", "text": "Exactly. That makes review easier tomorrow.", "translation": "沒錯。那會讓明天複習更容易。"},
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
                "immersion": {
                    "shadowing_text": [
                        {"speaker": "Coach", "text": "I review new words every day.", "translation": "我每天複習新單字。"},
                        {"speaker": "Coach", "text": "When a sentence is hard, I repeat one chunk.", "translation": "句子很難時，我重複一個片語。"},
                    ],
                    "repeat_chunks": ["start with a short review", "repeat three useful chunks", "in my own words"],
                    "listening_tips": ["Listen once for meaning.", "Shadow slowly before natural speed.", "Mark words that connect ideas."],
                },
                "feynman_prompt": {
                    "prompt": "Explain how a small study routine helps you remember English words.",
                    "checklist": ["Use at least three vocabulary words.", "Use one sentence pattern.", "Give one personal example."],
                },
            }
        else:
            words = [
                ("習慣", "しゅうかん", "習慣", "毎朝、短い復習をする習慣があります。", "每天早上我有做短複習的習慣。", "名詞", "習", "study"),
                ("復習", "ふくしゅう", "複習", "授業のあとで単語を復習します。", "上課後複習單字。", "名詞/動詞", "復", "review"),
                ("練習", "れんしゅう", "練習", "文型を声に出して練習します。", "把文型唸出聲練習。", "名詞/動詞", "練", "practice"),
                ("説明", "せつめい", "說明", "自分の言葉で説明します。", "用自己的話說明。", "名詞/動詞", "説", "output"),
                ("目標", "もくひょう", "目標", "今日の目標を三つ書きます。", "寫下今天三個目標。", "名詞", "目", "plan"),
                ("会話", "かいわ", "對話", "友だちと短い会話をします。", "和朋友做短對話。", "名詞", "会", "dialogue"),
                ("例文", "れいぶん", "例句", "新しい単語で例文を作ります。", "用新單字造例句。", "名詞", "例", "sentence"),
                ("聞く", "きく", "聽", "まず一回聞いて、意味を考えます。", "先聽一次並思考意思。", "動詞", "聞", "listening"),
            ]
            data = {
                "objectives": [f"{topic}に関する基本語彙を使う。", "三つの文型で短い文を作る。", "会話と読み物の内容を自分の言葉で説明する。"],
                "vocabulary": [
                    VocabularyItem(word=word, reading=reading, definition_zh=definition, example_sentence=example, example_translation=translation, part_of_speech=pos, root=root, word_family=[word], memory_tip=f"「{root}」から「{word}」を思い出しましょう。", category=category, tags=["fallback", category])
                    for word, reading, definition, example, translation, pos, root, category in words
                ],
                "word_roots": [
                    {"root": "復", "meaning_zh": "再一次、回復", "examples": ["復習", "復活", "往復"], "memory_tip": "「復」はもう一度戻るイメージ。"},
                    {"root": "習", "meaning_zh": "學習、反覆練習", "examples": ["習慣", "練習", "学習"], "memory_tip": "何度も練習して身につけるイメージ。"},
                    {"root": "会", "meaning_zh": "見面、聚集", "examples": ["会話", "会社", "会う"], "memory_tip": "人が集まって話す場面を想像する。"},
                ],
                "sentence_patterns": [
                    {"pattern": "〜があります", "meaning_zh": "有……", "usage_note": "用來說明自己有某種習慣或物品。", "examples": [{"sentence": "毎朝、復習する習慣があります。", "translation": "每天早上有複習的習慣。"}]},
                    {"pattern": "〜てから、〜ます", "meaning_zh": "做完……之後，做……", "usage_note": "用來描述順序。", "examples": [{"sentence": "聞いてから、声に出します。", "translation": "聽完之後唸出聲。"}]},
                    {"pattern": "〜と思います", "meaning_zh": "我覺得……", "usage_note": "用來表達想法。", "examples": [{"sentence": "短い練習は大切だと思います。", "translation": "我覺得短練習很重要。"}]},
                ],
                "grammar": GrammarSection(
                    title="習慣を話す文型",
                    explanation="毎日の行動を話すときは、現在形と時間の言葉を一緒に使います。",
                    examples=[{"sentence": "毎日、単語を復習します。", "translation": "每天複習單字。"}, {"sentence": "聞いてから、文を言います。", "translation": "聽完之後說句子。"}],
                    exercises=[
                        GrammarExercise(question="正しい文を選んでください。", options=["毎日、復習します。", "毎日、復習しましたか昨日。", "毎日、復習ですを。"], correct_answer="毎日、復習します。", explanation="毎日の習慣には現在形を使います。"),
                        GrammarExercise(question="「聞く」のて形はどれですか。", options=["聞いて", "聞きて", "聞くて"], correct_answer="聞いて", explanation="聞くのて形は聞いてです。"),
                        GrammarExercise(question="順序を表す文はどれですか。", options=["読んでから、説明します。", "読むからで、説明します。", "読みますからて、説明します。"], correct_answer="読んでから、説明します。", explanation="〜てから、〜ますで順序を表します。"),
                    ],
                ),
                "dialogue": DialogueSection(
                    scenario="授業後の復習計画",
                    context="二人の学生が今日の日本語レッスンについて話します。",
                    dialogue=[
                        {"speaker": "ミア", "text": "今日の単語を覚えたいです。", "translation": "我想記住今天的單字。"},
                        {"speaker": "ケン", "text": "まず短い復習をしましょう。", "translation": "先做短複習吧。"},
                        {"speaker": "ミア", "text": "全部もう一度読みますか。", "translation": "要全部再讀一次嗎？"},
                        {"speaker": "ケン", "text": "いいえ、便利な文を三つ練習します。", "translation": "不用，練習三個實用句子。"},
                        {"speaker": "ミア", "text": "それから自分の言葉で説明します。", "translation": "然後用自己的話說明。"},
                        {"speaker": "ケン", "text": "はい。明日の復習が楽になります。", "translation": "對。明天的複習會變輕鬆。"},
                    ],
                    alternatives=[],
                ),
                "reading": ReadingSection(
                    title="短い復習の力",
                    content="毎日、少しだけ日本語を復習します。まず、新しい単語を声に出します。次に、例文を一つ読みます。それから、便利な文型を使って自分の文を作ります。難しい文は、全部ではなく短い部分を練習します。会話を聞いて、まねして言います。最後に、今日の内容を自分の言葉で説明します。明日は同じ単語をもう一度見ます。この小さい習慣で、勉強が続けやすくなります。",
                    word_count=9,
                    questions=[
                        ReadingQuestion(question="読み物の主な考えは何ですか。", options=["短い復習は続けやすいです。", "復習は必要ありません。", "単語だけを書きます。"], correct_answer="短い復習は続けやすいです。", explanation="文章は小さい習慣の大切さを説明しています。"),
                        ReadingQuestion(question="難しい文はどうしますか。", options=["短い部分を練習します。", "すぐ全部やめます。", "早く読みます。"], correct_answer="短い部分を練習します。", explanation="全部ではなく短い部分を練習すると書いてあります。"),
                        ReadingQuestion(question="最後に何をしますか。", options=["自分の言葉で説明します。", "新しい本を買います。", "音声を消します。"], correct_answer="自分の言葉で説明します。", explanation="最後に内容を自分の言葉で説明します。"),
                    ],
                ),
                "immersion": {
                    "shadowing_text": [{"speaker": "先生", "text": "毎日、少しだけ復習します。", "translation": "每天只複習一點。"}, {"speaker": "先生", "text": "聞いてから、まねして言います。", "translation": "聽完之後模仿說出來。"}],
                    "repeat_chunks": ["少しだけ復習します", "聞いてから", "自分の言葉で"],
                    "listening_tips": ["一回目は意味を聞きます。", "二回目は短く区切ってまねします。", "助詞を小さく確認します。"],
                },
                "feynman_prompt": {"prompt": "短い復習がなぜ役に立つか、自分の言葉で説明してください。", "checklist": ["単語を三つ使う。", "文型を一つ使う。", "自分の例を一つ入れる。"]},
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
        return lesson


lesson_generator = LessonGenerator()
