"""Demo dataset reset and seed helpers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from config import settings
from database import Database
from models import UserRPGStats
from srs import srs_engine


def _local_now() -> datetime:
    """Return the current time in the app's configured timezone."""
    return datetime.now(ZoneInfo(settings.timezone))


def reset_demo_dataset(db: Database) -> dict[str, Any]:
    user_id = settings.default_user_id
    _clear_runtime_artifacts()
    _clear_database(db, user_id)
    db.save_diagnostic_state(
        user_id=user_id,
        estimated_total_days=90,
        current_day=1,
        summary_zh="Demo learner has completed the placement diagnostic and can start the seeded lesson flow.",
        correct_count=4,
    )

    now = _local_now()
    local_today = now.date()
    today_lesson_id = _seed_lesson(
        db,
        user_id=user_id,
        lesson_id="demo-en-today",
        language="EN",
        level="A2",
        topic="Daily Standup Conversations",
        generated_at=now,
        vocabulary=[
            {
                "word": "blocker",
                "phonetic": "/ˈblɑː.kɚ/",
                "definition_zh": "阻礙進度的問題",
                "example_sentence": "I have one blocker in the deployment step.",
                "example_translation": "我在部署步驟有一個阻礙。",
            },
            {
                "word": "ship",
                "phonetic": "/ʃɪp/",
                "definition_zh": "交付、上線",
                "example_sentence": "We can ship the fix this afternoon.",
                "example_translation": "我們今天下午可以上線這個修正。",
            },
        ],
        grammar={
            "title": "Present Simple for status updates",
            "explanation": "Use the present simple to report routines, status, and current work plans.",
            "examples": [
                {"sentence": "I review pull requests every morning.", "translation": "我每天早上都會 review PR。"}
            ],
            "exercises": [
                {
                    "question": "Choose the best standup update sentence.",
                    "options": [
                        "I finish the API docs today.",
                        "I am finish the API docs today.",
                        "I finished the API docs tomorrow.",
                    ],
                    "correct_answer": "I finish the API docs today.",
                    "explanation": "The present simple works for a planned status update in this demo.",
                }
            ],
        },
        reading={
            "title": "Demo Standup Note",
            "content": "Our team reviews the release checklist, fixes one blocker, and ships the lesson flow before noon.",
            "word_count": 16,
            "questions": [
                {
                    "question": "What does the team do before noon?",
                    "options": ["Ships the lesson flow", "Cancels the release", "Writes a novel"],
                    "correct_answer": "Ships the lesson flow",
                    "explanation": "The note says the team ships the lesson flow before noon.",
                }
            ],
        },
        dialogue={
            "scenario": "Morning standup",
            "context": "A short work update between teammates.",
            "dialogue": [
                {"speaker": "Aki", "text": "I fixed the blocker this morning.", "translation": "我今天早上修好了阻礙。"},
                {"speaker": "Mina", "text": "Great, then we can ship after lunch.", "translation": "太好了，那我們午餐後就能上線。"},
            ],
            "alternatives": [],
        },
    )

    _seed_lesson(
        db,
        user_id=user_id,
        lesson_id="demo-jp-archive",
        language="JP",
        level="N4",
        topic="Cafe Ordering Practice",
        generated_at=now - timedelta(days=1),
        vocabulary=[
            {
                "word": "注文",
                "reading": "ちゅうもん",
                "definition_zh": "點餐、下單",
                "example_sentence": "コーヒーを注文します。",
                "example_translation": "我要點咖啡。",
            },
            {
                "word": "おすすめ",
                "reading": "おすすめ",
                "definition_zh": "推薦",
                "example_sentence": "今日のおすすめは何ですか。",
                "example_translation": "今天的推薦是什麼？",
            },
        ],
        grammar={
            "title": "〜てもいいですか",
            "explanation": "Use this pattern to ask for permission politely.",
            "examples": [{"sentence": "ここに座ってもいいですか。", "translation": "我可以坐這裡嗎？"}],
            "exercises": [
                {
                    "question": "店内で写真を撮ってもいいですか。",
                    "options": ["Yes", "No"],
                    "correct_answer": "Yes",
                    "explanation": "This is a polite permission request example.",
                }
            ],
        },
        reading={
            "title": "Cafe Memo",
            "content": "おすすめのケーキは午後三時までです。",
            "word_count": 15,
            "questions": [
                {
                    "question": "おすすめのケーキはいつまでですか。",
                    "options": ["午後一時まで", "午後三時まで", "夜まで"],
                    "correct_answer": "午後三時まで",
                    "explanation": "The memo says it is available until 3 p.m.",
                }
            ],
        },
        dialogue={
            "scenario": "Cafe counter",
            "context": "Ordering politely in Japanese.",
            "dialogue": [
                {"speaker": "客", "text": "おすすめを一つお願いします。", "translation": "請給我一份推薦餐點。"},
                {"speaker": "店員", "text": "かしこまりました。", "translation": "好的，沒問題。"},
            ],
            "alternatives": [],
        },
    )

    imported_words: list[dict[str, Any]] = [
        {
            "language": "EN",
            "word": "retrospective",
            "reading": None,
            "definition_zh": "回顧會議",
            "example_sentence": "We discuss process improvements in the retrospective.",
            "example_translation": "我們在回顧會議討論流程改善。",
        },
        {
            "language": "JP",
            "word": "復習",
            "reading": "ふくしゅう",
            "definition_zh": "複習",
            "example_sentence": "毎晩、単語を復習します。",
            "example_translation": "我每天晚上複習單字。",
        },
    ]
    for item in imported_words:
        db.save_imported_vocabulary(user_id, item["language"], item)
        srs_data = srs_engine.calculate(quality=4, prev_interval=1, prev_ease_factor=2.5, repetition=1)
        db.update_srs_item(user_id, item["word"], item["language"], srs_data, item)

    db.upsert_wrong_answer(
        user_id=user_id,
        language="EN",
        question_type="grammar",
        question="Choose the best standup update sentence.",
        user_answer="I am finish the API docs today.",
        correct_answer="I finish the API docs today.",
        source_lesson_id=today_lesson_id,
    )
    db.upsert_wrong_answer(
        user_id=user_id,
        language="JP",
        question_type="reading",
        question="おすすめのケーキはいつまでですか。",
        user_answer="午後一時まで",
        correct_answer="午後三時まで",
        source_lesson_id="demo-jp-archive",
    )
    _seed_learning_intelligence_demo_data(
        db,
        user_id=user_id,
        source_lesson_id=today_lesson_id,
        now=now,
    )

    progress = db.get_progress(user_id)
    progress["english_progress"]["current_level"] = "A2"
    progress["english_progress"]["completed_lessons"] = 1
    progress["english_progress"]["total_exercises"] = 2
    progress["english_progress"]["correct_exercises"] = 1
    progress["english_progress"]["accuracy_rate"] = 50.0
    progress["english_progress"]["last_study_date"] = now.isoformat()
    progress["japanese_progress"]["current_level"] = "N4"
    progress["japanese_progress"]["completed_lessons"] = 1
    progress["japanese_progress"]["total_exercises"] = 2
    progress["japanese_progress"]["correct_exercises"] = 2
    progress["japanese_progress"]["accuracy_rate"] = 100.0
    progress["japanese_progress"]["last_study_date"] = (now - timedelta(days=1)).isoformat()

    stats = UserRPGStats(**progress["rpg_stats"])
    stats.is_onboarded = True
    stats.level = 3
    stats.current_xp = 40
    stats.next_level_xp = 519
    stats.total_xp = 240
    stats.streak_days = 3
    progress["rpg_stats"] = stats.model_dump(mode="json")
    db.save_progress(progress)

    db.save_generation_task(
        {
            "task_id": "demo-task-success",
            "user_id": user_id,
            "status": "success",
            "model_used": "demo-seed",
            "duration_ms": 1200,
            "retry_count": 0,
            "created_at": now.isoformat(),
        }
    )
    db.record_learning_activity(
        user_id=user_id,
        activity_type="generate_lesson",
        activity_date=(local_today - timedelta(days=2)).isoformat(),
        created_at=(now - timedelta(days=2)).isoformat(),
    )
    db.record_learning_activity(
        user_id=user_id,
        activity_type="review",
        activity_date=(local_today - timedelta(days=1)).isoformat(),
        created_at=(now - timedelta(days=1)).isoformat(),
    )
    db.record_learning_activity(
        user_id=user_id,
        activity_type="review",
        activity_date=local_today.isoformat(),
        created_at=now.isoformat(),
    )

    return {
        "lessons": 2,
        "imported_vocabulary": len(imported_words),
        "wrong_answers": 2,
        "today_lesson_id": today_lesson_id,
    }


def _clear_database(db: Database, user_id: str) -> None:
    tables = [
        "learning_item_reviews",
        "learning_item_srs",
        "feynman_feedback_history",
        "learning_items",
        "micro_lessons",
        "diagnostic_state",
        "generation_tasks",
        "exercise_results",
        "srs_vocabulary",
        "imported_vocabulary",
        "wrong_answers",
        "user_learning_activity",
        "progress",
        "lessons",
    ]
    with db.get_connection() as conn:
        conn.execute(
            """
            DELETE FROM learning_item_reviews
            WHERE item_id IN (
                SELECT id FROM learning_items WHERE user_id = ?
            )
            """,
            (user_id,),
        )
        conn.execute(
            """
            DELETE FROM learning_item_srs
            WHERE item_id IN (
                SELECT id FROM learning_items WHERE user_id = ?
            )
            """,
            (user_id,),
        )
        conn.execute("DELETE FROM feynman_feedback_history WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM learning_items WHERE user_id = ?", (user_id,))
        for table in tables[4:]:
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))


def _clear_runtime_artifacts() -> None:
    for path in (settings.lessons_dir, settings.audio_dir, settings.exports_dir, settings.data_path / "demo"):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)


def _seed_learning_intelligence_demo_data(
    db: Database,
    *,
    user_id: str,
    source_lesson_id: str,
    now: datetime,
) -> None:
    seeded_items: list[dict[str, Any]] = [
        {
            "item_type": "vocabulary",
            "item_key": "blocker",
            "language": "EN",
            "level": "A2",
            "category": "workflow",
            "tags": ["standup", "weak"],
            "content": {
                "word": "blocker",
                "definition_zh": "An issue that stops progress.",
                "root": "block",
                "memory_tip": "Picture a road block that pauses the task.",
            },
            "mastery_state": "weak",
            "due_at": now - timedelta(days=1),
            "last_reviewed_at": now - timedelta(hours=6),
            "interval_days": 1,
            "ease_factor": 2.1,
            "repetitions": 1,
            "lapses": 2,
        },
        {
            "item_type": "vocabulary",
            "item_key": "ship",
            "language": "EN",
            "level": "A2",
            "category": "workflow",
            "tags": ["recent"],
            "content": {
                "word": "ship",
                "definition_zh": "To release work for users.",
                "root": "ship",
                "memory_tip": "Imagine shipping a finished feature out the door.",
            },
            "mastery_state": "learning",
            "due_at": now + timedelta(days=2),
            "last_reviewed_at": now - timedelta(minutes=45),
            "interval_days": 2,
            "ease_factor": 2.5,
            "repetitions": 1,
            "lapses": 0,
        },
        {
            "item_type": "grammar",
            "item_key": "Present Simple for status updates",
            "language": "EN",
            "level": "A2",
            "category": "grammar",
            "tags": ["standup", "weak"],
            "content": {
                "title": "Present Simple for status updates",
                "explanation": "Use the present simple to describe routine updates and current work status.",
            },
            "mastery_state": "weak",
            "due_at": now - timedelta(hours=4),
            "last_reviewed_at": now - timedelta(hours=2),
            "interval_days": 1,
            "ease_factor": 2.2,
            "repetitions": 1,
            "lapses": 2,
        },
        {
            "item_type": "sentence_pattern",
            "item_key": "I report blockers in the standup.",
            "language": "EN",
            "level": "A2",
            "category": "sentence_pattern",
            "tags": ["snowball"],
            "content": {
                "pattern": "I report blockers in the standup.",
                "meaning_zh": "A sentence pattern for a short status update.",
            },
            "mastery_state": "learning",
            "due_at": now - timedelta(minutes=30),
            "last_reviewed_at": now - timedelta(days=1),
            "interval_days": 1,
            "ease_factor": 2.4,
            "repetitions": 1,
            "lapses": 0,
        },
    ]

    for item in seeded_items:
        db.upsert_learning_item(
            user_id=user_id,
            item_type=item["item_type"],
            item_key=item["item_key"],
            language=item["language"],
            level=item["level"],
            lesson_id=source_lesson_id,
            content=item["content"],
            category=item["category"],
            tags=item["tags"],
        )
        saved = db.get_learning_item_by_key(
            user_id=user_id,
            item_type=item["item_type"],
            item_key=item["item_key"],
            language=item["language"],
        )
        if not saved:
            continue
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE learning_item_srs
                SET interval_days = ?, ease_factor = ?, repetitions = ?, lapses = ?,
                    due_at = ?, last_reviewed_at = ?, mastery_state = ?
                WHERE item_id = ?
                """,
                (
                    item["interval_days"],
                    item["ease_factor"],
                    item["repetitions"],
                    item["lapses"],
                    item["due_at"].isoformat(),
                    item["last_reviewed_at"].isoformat(),
                    item["mastery_state"],
                    str(saved["id"]),
                ),
            )


def _seed_lesson(
    db: Database,
    *,
    user_id: str,
    lesson_id: str,
    language: str,
    level: str,
    topic: str,
    generated_at: datetime,
    vocabulary: list[dict[str, Any]],
    grammar: dict[str, Any],
    reading: dict[str, Any],
    dialogue: dict[str, Any],
) -> str:
    payload = {
        "metadata": {
            "lesson_id": lesson_id,
            "language": language,
            "level": level,
            "topic": topic,
            "generated_at": generated_at.isoformat(),
            "estimated_duration_minutes": 20,
            "key_points": [topic, level],
        },
        "vocabulary": vocabulary,
        "grammar": grammar,
        "reading": reading,
        "dialogue": dialogue,
        "evidence": [],
    }
    lesson_dir = settings.lessons_dir / generated_at.strftime("%Y-%m-%d")
    lesson_dir.mkdir(parents=True, exist_ok=True)
    file_path = lesson_dir / f"lesson_{lesson_id}.json"
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    db.save_lesson(payload, str(file_path), user_id=user_id)
    return lesson_id
