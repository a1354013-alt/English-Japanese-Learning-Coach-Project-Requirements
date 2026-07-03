"""Daily micro lesson mode for beginner English coaching."""

from __future__ import annotations

from api_errors import COMMON_ERROR_RESPONSES, api_error
from database import db
from fastapi import APIRouter, Depends
from gamification_engine import gamification_engine
from models import (
    DiagnosticQuestion,
    DiagnosticQuestionsResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    FillBlankQuestion,
    LearningPlan,
    MicroDialogueLine,
    MicroLesson,
    MicroLessonAnswerRequest,
    MicroLessonAnswerResponse,
    MicroLessonResponse,
    MicroLessonTodayResponse,
    MicroVocabularyItem,
    ComicPanel,
)
from routers.deps import require_demo_user_id
from services.streak_service import get_streak_snapshot

router = APIRouter(prefix="/api", tags=["micro-lessons"], responses=COMMON_ERROR_RESPONSES)

DIAGNOSTIC_QUESTIONS = [
    DiagnosticQuestion(
        question_id="subject-1",
        prompt="In 'The manager checks email,' which words are the subject?",
        choices=["The manager", "checks", "email"],
        correct_answer="The manager",
        skill="subject",
    ),
    DiagnosticQuestion(
        question_id="verb-1",
        prompt="In 'We raise prices,' which word is the verb?",
        choices=["We", "raise", "prices"],
        correct_answer="raise",
        skill="verb",
    ),
    DiagnosticQuestion(
        question_id="present-1",
        prompt="Choose the basic present simple sentence.",
        choices=["She works today.", "She working today.", "She worked today."],
        correct_answer="She works today.",
        skill="present_simple",
    ),
    DiagnosticQuestion(
        question_id="subject-2",
        prompt="In 'Customers need help,' which word is the subject?",
        choices=["Customers", "need", "help"],
        correct_answer="Customers",
        skill="subject",
    ),
]


@router.get("/diagnostic/questions", response_model=DiagnosticQuestionsResponse)
async def get_diagnostic_questions():
    return {"success": True, "questions": DIAGNOSTIC_QUESTIONS}


@router.post("/diagnostic/submit", response_model=DiagnosticSubmitResponse)
async def submit_diagnostic(
    request: DiagnosticSubmitRequest,
    user_id: str = Depends(require_demo_user_id),
):
    answer_map = {item.question_id: item.answer.strip() for item in request.answers}
    correct_count = 0
    for question in DIAGNOSTIC_QUESTIONS:
        if answer_map.get(question.question_id) == question.correct_answer:
            correct_count += 1

    if correct_count >= 4:
        estimated_total_days = 90
        summary_zh = "你已能掌握主詞、動詞與基本現在式，建議用 90 天建立 TOEIC 600 基礎。"
    elif correct_count >= 2:
        estimated_total_days = 120
        summary_zh = "你能辨認部分句子結構，建議用 120 天每天練短句、單字與填空。"
    else:
        estimated_total_days = 150
        summary_zh = "你適合從最小句型開始，建議用 150 天慢慢建立主詞、動詞與現在式直覺。"

    plan = db.save_diagnostic_state(
        user_id=user_id,
        estimated_total_days=estimated_total_days,
        current_day=1,
        summary_zh=summary_zh,
        correct_count=correct_count,
    )
    return {"success": True, "learning_plan": plan}


@router.get("/micro-lessons/today", response_model=MicroLessonTodayResponse)
async def get_today_micro_lesson(user_id: str = Depends(require_demo_user_id)):
    state = db.get_diagnostic_state(user_id)
    if not state:
        return {"success": True, "diagnostic_completed": False, "learning_plan": None, "lesson": None}

    plan = _learning_plan_from_state(state)
    lesson = db.get_micro_lesson_by_day(user_id, plan.current_day)
    if not lesson:
        lesson = _build_micro_lesson(day_index=plan.current_day, total_days=plan.estimated_total_days).model_dump()
        db.save_micro_lesson(user_id, lesson)

    return {"success": True, "diagnostic_completed": True, "learning_plan": plan, "lesson": lesson}


@router.post("/micro-lessons/generate", response_model=MicroLessonResponse)
async def generate_micro_lesson(user_id: str = Depends(require_demo_user_id)):
    state = db.get_diagnostic_state(user_id)
    if not state:
        state = db.save_diagnostic_state(
            user_id=user_id,
            estimated_total_days=90,
            current_day=1,
            summary_zh="尚未完成診斷，先提供 90 天 TOEIC 600 入門微課。",
            correct_count=0,
        )
    plan = _learning_plan_from_state(state)
    lesson = _build_micro_lesson(day_index=plan.current_day, total_days=plan.estimated_total_days)
    db.save_micro_lesson(user_id, lesson.model_dump())
    return {"success": True, "lesson": lesson}


@router.post("/micro-lessons/{lesson_id}/answer", response_model=MicroLessonAnswerResponse)
async def answer_micro_lesson(
    lesson_id: str,
    request: MicroLessonAnswerRequest,
    user_id: str = Depends(require_demo_user_id),
):
    lesson = db.get_micro_lesson_by_id(user_id, lesson_id)
    if not lesson:
        raise api_error(404, "Micro lesson not found", "micro_lesson_not_found")

    expected = str(lesson["fill_blank_question"]["correct_answer"]).strip().lower()
    correct = request.answer.strip().lower() == expected
    was_completed = bool(lesson.get("completed"))
    if correct:
        lesson = db.mark_micro_lesson_completed(user_id, lesson_id) or lesson
        if not was_completed:
            db.record_learning_activity(user_id=user_id, activity_type="micro_lesson")
            _update_micro_progress(user_id)
            gamification_engine.add_xp(user_id, 10)

    streak = get_streak_snapshot(user_id)
    return {"success": True, "correct": correct, "completed": bool(lesson.get("completed")), "lesson": lesson, "streak": streak}


def _learning_plan_from_state(state: dict) -> LearningPlan:
    return LearningPlan(
        estimated_total_days=int(state["estimated_total_days"]),
        current_day=int(state["current_day"]),
        summary_zh=str(state["summary_zh"]),
    )


def _build_micro_lesson(day_index: int, total_days: int) -> MicroLesson:
    return MicroLesson(
        day_index=day_index,
        total_days=total_days,
        target_exam="TOEIC 600",
        sentence="We raise prices today.",
        translation_zh="我們今天調高價格。",
        subject_text="We",
        verb_text="raise",
        object_text="prices",
        reading_order_steps=[
            "先找主詞 We：誰做這件事。",
            "再找動詞 raise：做了什麼動作。",
            "最後接 object prices：動作影響什麼。",
        ],
        grammar_note="現在簡單式描述日常、事實或今天安排。主詞 We 搭配原形動詞 raise。",
        toeic_usage_note="TOEIC 常用 raise prices / raise questions / raise concerns 表示提高或提出。",
        vocabulary_items=[
            MicroVocabularyItem(
                word="raise",
                phonetic="/reɪz/",
                pronunciation_zh="雷茲",
                definition_zh="提高；提出",
                example_sentence="We raise prices today.",
                example_translation="我們今天調高價格。",
            ),
            MicroVocabularyItem(
                word="price",
                phonetic="/praɪs/",
                pronunciation_zh="普賴斯",
                definition_zh="價格",
                example_sentence="The price is high.",
                example_translation="價格很高。",
            ),
            MicroVocabularyItem(
                word="today",
                phonetic="/təˈdeɪ/",
                pronunciation_zh="特-day",
                definition_zh="今天",
                example_sentence="We meet today.",
                example_translation="我們今天見面。",
            ),
            MicroVocabularyItem(
                word="customer",
                phonetic="/ˈkʌstəmər/",
                pronunciation_zh="卡斯特默",
                definition_zh="顧客",
                example_sentence="Customers need help.",
                example_translation="顧客需要協助。",
            ),
            MicroVocabularyItem(
                word="report",
                phonetic="/rɪˈpɔːrt/",
                pronunciation_zh="瑞波特",
                definition_zh="報告",
                example_sentence="I read the report.",
                example_translation="我閱讀報告。",
            ),
        ],
        dialogue_lines=[
            MicroDialogueLine(speaker="A", english="Do we raise prices today?", translation_zh="我們今天調高價格嗎？"),
            MicroDialogueLine(speaker="B", english="Yes, we raise prices today.", translation_zh="是的，我們今天調高價格。"),
        ],
        reading_passage="A team checks the report. They raise prices today. Customers see the new price.",
        comic_panels=[
            ComicPanel(panel=1, english="We check the report.", translation_zh="我們查看報告。", scene_prompt="Office team reading a simple report."),
            ComicPanel(panel=2, english="The price is low.", translation_zh="價格偏低。", scene_prompt="A price tag on a desk."),
            ComicPanel(panel=3, english="We raise prices today.", translation_zh="我們今天調高價格。", scene_prompt="Manager pointing at a price chart."),
            ComicPanel(panel=4, english="Customers see the price.", translation_zh="顧客看到價格。", scene_prompt="Customer looking at a clear price label."),
        ],
        fill_blank_question=FillBlankQuestion(
            prompt="We ___ prices today.",
            choices=["raise", "raises", "raising"],
            correct_answer="raise",
            explanation="主詞 We 搭配現在簡單式原形動詞 raise。",
        ),
    )


def _update_micro_progress(user_id: str) -> None:
    progress = db.get_progress(user_id)
    english = progress["english_progress"]
    english["completed_lessons"] = int(english.get("completed_lessons", 0)) + 1
    english["total_exercises"] = int(english.get("total_exercises", 0)) + 1
    english["correct_exercises"] = int(english.get("correct_exercises", 0)) + 1
    total = max(1, int(english["total_exercises"]))
    english["accuracy_rate"] = round(int(english["correct_exercises"]) / total * 100, 2)
    english["last_study_date"] = db._local_date_str()
    progress["english_progress"] = english
    db.save_progress(progress)
