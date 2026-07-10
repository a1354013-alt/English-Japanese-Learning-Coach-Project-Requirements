"""Reusable deterministic micro lesson helpers."""

from __future__ import annotations

from typing import cast

from models import (
    ComicPanel,
    FillBlankQuestion,
    LearningPlan,
    MicroDialogueLine,
    MicroLesson,
    MicroVocabularyItem,
)


def learning_plan_from_state(state: dict) -> LearningPlan:
    return LearningPlan(
        estimated_total_days=int(state["estimated_total_days"]),
        current_day=int(state["current_day"]),
        summary_zh=str(state["summary_zh"]),
    )


def _vocab(word: str, definition: str, example: str) -> MicroVocabularyItem:
    return MicroVocabularyItem(
        word=word,
        phonetic=f"/{word}/",
        pronunciation_zh=word,
        definition_zh=definition,
        example_sentence=example,
        example_translation=f"Example: {example}",
    )


MICRO_LESSON_TEMPLATES: list[dict[str, object]] = [
    {
        "theme": "subject/verb/object",
        "sentence": "We raise prices today.",
        "translation_zh": "We raise prices today.",
        "subject_text": "We",
        "verb_text": "raise",
        "object_text": "prices",
        "grammar_note": "A simple business sentence often follows subject, verb, then object.",
        "toeic_usage_note": "TOEIC notices often use raise prices, raise questions, and raise concerns.",
        "blank": "We ___ prices today.",
        "choices": ["raise", "raises", "raising"],
        "answer": "raise",
        "words": [
            ("raise", "increase", "We raise prices today."),
            ("price", "cost", "The price is high."),
            ("today", "this day", "We meet today."),
            ("customer", "buyer", "Customers need help."),
            ("report", "business document", "I read the report."),
        ],
    },
    {
        "theme": "present simple",
        "sentence": "She checks email every morning.",
        "translation_zh": "She checks email every morning.",
        "subject_text": "She",
        "verb_text": "checks",
        "object_text": "email",
        "grammar_note": "Use present simple for routines. Add -s or -es after he, she, or it.",
        "toeic_usage_note": "Work routines in TOEIC often use present simple verbs.",
        "blank": "She ___ email every morning.",
        "choices": ["checks", "check", "checking"],
        "answer": "checks",
        "words": [
            ("check", "look at carefully", "She checks email every morning."),
            ("email", "electronic mail", "I send an email."),
            ("morning", "early part of the day", "The meeting is in the morning."),
            ("routine", "regular habit", "This is my routine."),
            ("desk", "work table", "The file is on the desk."),
        ],
    },
    {
        "theme": "be verb",
        "sentence": "The report is ready.",
        "translation_zh": "The report is ready.",
        "subject_text": "The report",
        "verb_text": "is",
        "object_text": "ready",
        "grammar_note": "Use be verbs to connect a subject with a state or description.",
        "toeic_usage_note": "Office updates often say a report is ready or a room is available.",
        "blank": "The report ___ ready.",
        "choices": ["is", "are", "be"],
        "answer": "is",
        "words": [
            ("report", "business document", "The report is ready."),
            ("ready", "prepared", "The room is ready."),
            ("available", "free to use", "The manager is available."),
            ("room", "meeting space", "The room is quiet."),
            ("file", "document", "The file is ready."),
        ],
    },
    {
        "theme": "noun phrase",
        "sentence": "The new invoice needs approval.",
        "translation_zh": "The new invoice needs approval.",
        "subject_text": "The new invoice",
        "verb_text": "needs",
        "object_text": "approval",
        "grammar_note": "A noun phrase can include small words before the main noun.",
        "toeic_usage_note": "Invoices, forms, and requests often need approval in TOEIC messages.",
        "blank": "The new invoice ___ approval.",
        "choices": ["needs", "need", "needing"],
        "answer": "needs",
        "words": [
            ("invoice", "bill", "The invoice needs approval."),
            ("approval", "permission", "We need approval today."),
            ("new", "not old", "This is a new form."),
            ("form", "document to fill in", "Please sign the form."),
            ("request", "thing asked for", "The request is urgent."),
        ],
    },
    {
        "theme": "TOEIC email sentence",
        "sentence": "Please confirm the meeting time.",
        "translation_zh": "Please confirm the meeting time.",
        "subject_text": "Please",
        "verb_text": "confirm",
        "object_text": "the meeting time",
        "grammar_note": "Please plus a base verb makes a polite email request.",
        "toeic_usage_note": "TOEIC emails often ask readers to confirm, review, or attach information.",
        "blank": "Please ___ the meeting time.",
        "choices": ["confirm", "confirms", "confirmed"],
        "answer": "confirm",
        "words": [
            ("confirm", "make sure", "Please confirm the meeting time."),
            ("meeting", "planned discussion", "The meeting starts at ten."),
            ("time", "hour or minute", "What time is the call?"),
            ("attach", "add a file", "Please attach the file."),
            ("review", "check again", "Please review the note."),
        ],
    },
    {
        "theme": "business phone sentence",
        "sentence": "May I speak with Anna?",
        "translation_zh": "May I speak with Anna?",
        "subject_text": "I",
        "verb_text": "speak",
        "object_text": "with Anna",
        "grammar_note": "May I plus a base verb is a polite phone expression.",
        "toeic_usage_note": "Phone messages in TOEIC often use May I speak with...?",
        "blank": "May I ___ with Anna?",
        "choices": ["speak", "speaks", "speaking"],
        "answer": "speak",
        "words": [
            ("speak", "talk", "May I speak with Anna?"),
            ("call", "phone conversation", "I have a call."),
            ("message", "short note", "Please leave a message."),
            ("available", "free now", "Anna is available now."),
            ("phone", "calling device", "The phone is ringing."),
        ],
    },
    {
        "theme": "review day",
        "sentence": "We review one sentence again.",
        "translation_zh": "We review one sentence again.",
        "subject_text": "We",
        "verb_text": "review",
        "object_text": "one sentence",
        "grammar_note": "Review days reuse old patterns so they become faster and easier.",
        "toeic_usage_note": "A short review strengthens email, phone, and office sentence patterns.",
        "blank": "We ___ one sentence again.",
        "choices": ["review", "reviews", "reviewing"],
        "answer": "review",
        "words": [
            ("review", "check again", "We review one sentence again."),
            ("sentence", "group of words", "This sentence is useful."),
            ("again", "one more time", "Please say it again."),
            ("practice", "repeat to improve", "Practice every day."),
            ("goal", "target", "My goal is clear."),
        ],
    },
]


def build_micro_lesson(day_index: int, total_days: int) -> MicroLesson:
    template = MICRO_LESSON_TEMPLATES[(day_index - 1) % len(MICRO_LESSON_TEMPLATES)]
    template_words = cast(list[tuple[str, str, str]], template["words"])
    template_choices = cast(list[str], template["choices"])
    sentence = str(template["sentence"])
    words = [_vocab(str(word), str(definition), str(example)) for word, definition, example in template_words]

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
            MicroDialogueLine(speaker="B", english="Good. Please say it again.", translation_zh="Good. Please say it again."),
        ],
        reading_passage=(
            "A learner reads the sentence. The coach asks for the subject, verb, "
            f"and object. The learner says: {sentence}"
        ),
        comic_panels=[
            ComicPanel(
                panel=1,
                english=f"Day {day_index}: {template['theme']}",
                translation_zh="Daily micro lesson",
                scene_prompt="A friendly coach showing a sentence card.",
            ),
            ComicPanel(
                panel=2,
                english=f"Subject: {template['subject_text']}",
                translation_zh="Subject",
                scene_prompt="Highlight the subject phrase.",
            ),
            ComicPanel(panel=3, english=f"Verb: {template['verb_text']}", translation_zh="Verb", scene_prompt="Highlight the verb."),
            ComicPanel(
                panel=4,
                english=sentence,
                translation_zh=str(template["translation_zh"]),
                scene_prompt="Learner reading the full sentence.",
            ),
        ],
        fill_blank_question=FillBlankQuestion(
            prompt=str(template["blank"]),
            choices=[str(choice) for choice in template_choices],
            correct_answer=str(template["answer"]),
            explanation=str(template["grammar_note"]),
        ),
    )
