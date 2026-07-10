"""Daily micro lesson mode for beginner English coaching."""

from __future__ import annotations

from typing import cast

from api_errors import COMMON_ERROR_RESPONSES, api_error
from database import db
from fastapi import APIRouter, Depends
from gamification_engine import gamification_engine
from models import (
    ComicPanel,
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
)
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


def _build_micro_lesson_legacy(day_index: int, total_days: int) -> MicroLesson:
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


def _vocab(word: str, definition: str, example: str) -> MicroVocabularyItem:
    return MicroVocabularyItem(
        word=word,
        phonetic=f"/{word}/",
        pronunciation_zh=word,
        definition_zh=definition,
        example_sentence=example,
        example_translation=f"{example} 的意思。",
    )


MICRO_LESSON_TEMPLATES: list[dict[str, object]] = [
    {
        "theme": "subject/verb/object",
        "sentence": "We raise prices today.",
        "translation_zh": "我們今天調高價格。",
        "subject_text": "We",
        "verb_text": "raise",
        "object_text": "prices",
        "grammar_note": "A simple business sentence often follows subject, verb, then object.",
        "toeic_usage_note": "TOEIC notices often use raise prices, raise questions, and raise concerns.",
        "blank": "We ___ prices today.",
        "choices": ["raise", "raises", "raising"],
        "answer": "raise",
        "words": [("raise", "提高", "We raise prices today."), ("price", "價格", "The price is high."), ("today", "今天", "We meet today."), ("customer", "顧客", "Customers need help."), ("report", "報告", "I read the report.")],
    },
    {
        "theme": "present simple",
        "sentence": "She checks email every morning.",
        "translation_zh": "她每天早上查看電子郵件。",
        "subject_text": "She",
        "verb_text": "checks",
        "object_text": "email",
        "grammar_note": "Use present simple for routines. Add -s or -es after he, she, or it.",
        "toeic_usage_note": "Work routines in TOEIC often use present simple verbs.",
        "blank": "She ___ email every morning.",
        "choices": ["checks", "check", "checking"],
        "answer": "checks",
        "words": [("check", "查看", "She checks email every morning."), ("email", "電子郵件", "I send an email."), ("morning", "早上", "The meeting is in the morning."), ("routine", "例行事項", "This is my routine."), ("desk", "辦公桌", "The file is on the desk.")],
    },
    {
        "theme": "be verb",
        "sentence": "The report is ready.",
        "translation_zh": "報告準備好了。",
        "subject_text": "The report",
        "verb_text": "is",
        "object_text": "ready",
        "grammar_note": "Use be verbs to connect a subject with a state or description.",
        "toeic_usage_note": "Office updates often say a report is ready or a room is available.",
        "blank": "The report ___ ready.",
        "choices": ["is", "are", "be"],
        "answer": "is",
        "words": [("report", "報告", "The report is ready."), ("ready", "準備好的", "The room is ready."), ("available", "可用的", "The manager is available."), ("room", "房間", "The room is quiet."), ("file", "檔案", "The file is ready.")],
    },
    {
        "theme": "noun phrase",
        "sentence": "The new invoice needs approval.",
        "translation_zh": "新的發票需要核准。",
        "subject_text": "The new invoice",
        "verb_text": "needs",
        "object_text": "approval",
        "grammar_note": "A noun phrase can include small words before the main noun.",
        "toeic_usage_note": "Invoices, forms, and requests often need approval in TOEIC messages.",
        "blank": "The new invoice ___ approval.",
        "choices": ["needs", "need", "needing"],
        "answer": "needs",
        "words": [("invoice", "發票", "The invoice needs approval."), ("approval", "核准", "We need approval today."), ("new", "新的", "This is a new form."), ("form", "表格", "Please sign the form."), ("request", "請求", "The request is urgent.")],
    },
    {
        "theme": "TOEIC email sentence",
        "sentence": "Please confirm the meeting time.",
        "translation_zh": "請確認會議時間。",
        "subject_text": "Please",
        "verb_text": "confirm",
        "object_text": "the meeting time",
        "grammar_note": "Please plus a base verb makes a polite email request.",
        "toeic_usage_note": "TOEIC emails often ask readers to confirm, review, or attach information.",
        "blank": "Please ___ the meeting time.",
        "choices": ["confirm", "confirms", "confirmed"],
        "answer": "confirm",
        "words": [("confirm", "確認", "Please confirm the meeting time."), ("meeting", "會議", "The meeting starts at ten."), ("time", "時間", "What time is the call?"), ("attach", "附上", "Please attach the file."), ("review", "檢閱", "Please review the note.")],
    },
    {
        "theme": "business phone sentence",
        "sentence": "May I speak with Anna?",
        "translation_zh": "我可以和 Anna 通話嗎？",
        "subject_text": "I",
        "verb_text": "speak",
        "object_text": "with Anna",
        "grammar_note": "May I plus a base verb is a polite phone expression.",
        "toeic_usage_note": "Phone messages in TOEIC often use May I speak with...?",
        "blank": "May I ___ with Anna?",
        "choices": ["speak", "speaks", "speaking"],
        "answer": "speak",
        "words": [("speak", "說話", "May I speak with Anna?"), ("call", "電話", "I have a call."), ("message", "訊息", "Please leave a message."), ("available", "有空的", "Anna is available now."), ("phone", "電話", "The phone is ringing.")],
    },
    {
        "theme": "review day",
        "sentence": "We review one sentence again.",
        "translation_zh": "我們再次複習一個句子。",
        "subject_text": "We",
        "verb_text": "review",
        "object_text": "one sentence",
        "grammar_note": "Review days reuse old patterns so they become faster and easier.",
        "toeic_usage_note": "A short review strengthens email, phone, and office sentence patterns.",
        "blank": "We ___ one sentence again.",
        "choices": ["review", "reviews", "reviewing"],
        "answer": "review",
        "words": [("review", "複習", "We review one sentence again."), ("sentence", "句子", "This sentence is useful."), ("again", "再次", "Please say it again."), ("practice", "練習", "Practice every day."), ("goal", "目標", "My goal is clear.")],
    },
]


def _build_micro_lesson(day_index: int, total_days: int) -> MicroLesson:
    template = MICRO_LESSON_TEMPLATES[(day_index - 1) % len(MICRO_LESSON_TEMPLATES)]
    template_words = cast(list[tuple[str, str, str]], template["words"])
    template_choices = cast(list[str], template["choices"])
    words = [
        _vocab(str(word), str(definition), str(example))
        for word, definition, example in template_words
    ]
    sentence = str(template["sentence"])
    return MicroLesson(
        day_index=day_index,
        total_days=total_days,
        target_exam="TOEIC 600",
        sentence=sentence,
        translation_zh=str(template["translation_zh"]),
        subject_text=str(template["subject_text"]),
        verb_text=str(template["verb_text"]),
        object_text=str(template["object_text"]),
        reading_order_steps=[
            f"Find the subject: {template['subject_text']}.",
            f"Find the verb: {template['verb_text']}.",
            f"Find the object or complement: {template['object_text']}.",
        ],
        grammar_note=str(template["grammar_note"]),
        toeic_usage_note=str(template["toeic_usage_note"]),
        vocabulary_items=words,
        dialogue_lines=[
            MicroDialogueLine(speaker="A", english=sentence, translation_zh=str(template["translation_zh"])),
            MicroDialogueLine(speaker="B", english="Good. Please say it again.", translation_zh="很好。請再說一次。"),
        ],
        reading_passage=f"A learner reads the sentence. The coach asks for the subject, verb, and object. The learner says: {sentence}",
        comic_panels=[
            ComicPanel(panel=1, english=f"Day {day_index}: {template['theme']}", translation_zh="今日重點", scene_prompt="A friendly coach showing a sentence card."),
            ComicPanel(panel=2, english=f"Subject: {template['subject_text']}", translation_zh="主詞", scene_prompt="Highlight the subject phrase."),
            ComicPanel(panel=3, english=f"Verb: {template['verb_text']}", translation_zh="動詞", scene_prompt="Highlight the verb."),
            ComicPanel(panel=4, english=sentence, translation_zh=str(template["translation_zh"]), scene_prompt="Learner reading the full sentence."),
        ],
        fill_blank_question=FillBlankQuestion(
            prompt=str(template["blank"]),
            choices=[str(choice) for choice in template_choices],
            correct_answer=str(template["answer"]),
            explanation=str(template["grammar_note"]),
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
