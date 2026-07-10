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
    MicroLessonAnswerRequest,
    MicroLessonAnswerResponse,
    MicroLessonResponse,
    MicroLessonTodayResponse,
)
from services.micro_lesson_service import build_micro_lesson, learning_plan_from_state
from services.streak_service import get_streak_snapshot

from routers.deps import require_demo_user_id

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
        summary_zh = "Placement complete: start a 90-day TOEIC 600 micro lesson plan."
    elif correct_count >= 2:
        estimated_total_days = 120
        summary_zh = "Placement complete: start a 120-day foundation review plan."
    else:
        estimated_total_days = 150
        summary_zh = "Placement complete: start a 150-day beginner support plan."

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

    plan = learning_plan_from_state(state)
    lesson = db.get_micro_lesson_by_day(user_id, plan.current_day)
    if not lesson:
        lesson = build_micro_lesson(day_index=plan.current_day, total_days=plan.estimated_total_days).model_dump()
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
            summary_zh="Demo learner is ready for a 90-day TOEIC 600 micro lesson plan.",
            correct_count=0,
        )
    plan = learning_plan_from_state(state)
    lesson = build_micro_lesson(day_index=plan.current_day, total_days=plan.estimated_total_days)
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
