"""Additive learning-intelligence helpers for v1.3 item SRS, snowballing, and Feynman feedback."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from database import db
from models import FeynmanFeedback
from ollama_client import ollama_client


def sync_lesson_items(
    *,
    user_id: str,
    lesson_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    metadata = lesson_data.get("metadata", {})
    return db.sync_lesson_items_to_learning_items(
        user_id=user_id,
        lesson_data=lesson_data,
        language=str(metadata.get("language", "")),
        level=str(metadata.get("level", "")) if metadata.get("level") else None,
        lesson_id=str(metadata.get("lesson_id", "")) if metadata.get("lesson_id") else None,
    )


def sync_imported_vocabulary_item(*, user_id: str, language: str, item: Dict[str, Any]) -> Dict[str, Any]:
    tags = [str(tag) for tag in item.get("tags", []) if str(tag).strip()]
    return db.upsert_learning_item(
        user_id=user_id,
        item_type="vocabulary",
        item_key=str(item.get("word", "")).strip(),
        language=language,
        level=None,
        lesson_id=str(item.get("source_lesson_id", "")) if item.get("source_lesson_id") else None,
        content=item,
        category=str(item.get("category", "")).strip() if item.get("category") else None,
        tags=tags,
    )


def build_snowball_context(user_id: str, language: str, level: str | None) -> Dict[str, List[Dict[str, Any]]]:
    weak_items = db.get_weak_learning_items(user_id=user_id, language=language, limit=12)
    recent_vocab = db.get_recent_learning_items(
        user_id=user_id,
        language=language,
        item_type="vocabulary",
        limit=10,
    )
    recent_patterns = db.get_recent_learning_items(
        user_id=user_id,
        language=language,
        item_type="sentence_pattern",
        limit=6,
    )
    mastered_items = [
        item
        for item in db.get_recent_learning_items(user_id=user_id, language=language, limit=24)
        if str(item.get("mastery_state")) == "mastered"
    ][:5]

    return {
        "weak_vocabulary": _serialize_items(_filter_items(weak_items, "vocabulary")),
        "weak_grammar": _serialize_items(_filter_items(weak_items, "grammar")),
        "recent_vocabulary": _serialize_items(recent_vocab),
        "recent_sentence_patterns": _serialize_items(recent_patterns),
        "mastered_items_sample": _serialize_items(mastered_items),
    }


def _filter_items(items: Iterable[Dict[str, Any]], item_type: str) -> List[Dict[str, Any]]:
    return [item for item in items if str(item.get("item_type")) == item_type]


def _serialize_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in items:
        content = item.get("content") if isinstance(item.get("content"), dict) else {}
        result.append(
            {
                "item_id": item.get("id"),
                "item_type": item.get("item_type"),
                "item_key": item.get("item_key"),
                "category": item.get("category"),
                "tags": item.get("tags", []),
                "mastery_state": item.get("mastery_state"),
                "content": content,
            }
        )
    return result


def apply_item_reviews_from_lesson(
    *,
    user_id: str,
    lesson_data: Dict[str, Any],
    answer_checks: List[Tuple[str, int, bool]],
) -> int:
    sync_lesson_items(user_id=user_id, lesson_data=lesson_data)
    metadata = lesson_data.get("metadata", {})
    language = str(metadata.get("language", ""))
    updated_count = 0
    seen_pairs: set[tuple[str, str]] = set()

    for exercise_type, question_index, correct in answer_checks:
        section: Dict[str, Any]
        items: List[Dict[str, Any]]
        if exercise_type == "grammar":
            section = lesson_data.get("grammar", {})
            items = section.get("exercises", []) if isinstance(section, dict) else []
        else:
            section = lesson_data.get("reading", {})
            items = section.get("questions", []) if isinstance(section, dict) else []

        if question_index < 0 or question_index >= len(items):
            continue
        item = items[question_index]
        if not isinstance(item, dict):
            continue

        refs = [
            ("vocabulary", item.get("related_vocabulary", [])),
            ("grammar", item.get("related_grammar", [])),
            ("sentence_pattern", item.get("related_sentence_patterns", [])),
        ]
        has_refs = False
        for item_type, values in refs:
            for raw_key in values if isinstance(values, list) else []:
                key = str(raw_key).strip()
                if not key or (item_type, key) in seen_pairs:
                    continue
                learning_item = db.get_learning_item_by_key(
                    user_id=user_id,
                    item_type=item_type,
                    item_key=key,
                    language=language,
                )
                if not learning_item:
                    continue
                has_refs = True
                seen_pairs.add((item_type, key))
                db.record_learning_item_review(
                    user_id=user_id,
                    item_id=str(learning_item["id"]),
                    rating=4 if correct else 1,
                    correct=correct,
                    source="lesson_review",
                )
                updated_count += 1
        if not has_refs:
            continue

    return updated_count


async def generate_feynman_feedback(
    *,
    user_id: str,
    lesson_id: str,
    language: str,
    explanation: str,
    lesson_data: Dict[str, Any],
) -> FeynmanFeedback:
    sync_lesson_items(user_id=user_id, lesson_data=lesson_data)

    feedback = await _generate_feynman_feedback_with_model(
        language=language,
        explanation=explanation,
        lesson_data=lesson_data,
    )
    if feedback is None:
        feedback = _build_feynman_fallback_feedback(
            language=language,
            explanation=explanation,
            lesson_data=lesson_data,
        )

    db.save_feynman_feedback_history(
        user_id=user_id,
        lesson_id=lesson_id,
        explanation=explanation,
        feedback=feedback.model_dump(mode="json"),
    )
    _mark_missing_items_from_feedback(
        user_id=user_id,
        language=language,
        feedback=feedback,
    )
    return feedback


async def _generate_feynman_feedback_with_model(
    *,
    language: str,
    explanation: str,
    lesson_data: Dict[str, Any],
) -> FeynmanFeedback | None:
    lesson_summary = {
        "objectives": lesson_data.get("objectives", []),
        "vocabulary": [item.get("word") for item in lesson_data.get("vocabulary", []) if isinstance(item, dict)],
        "grammar_title": lesson_data.get("grammar", {}).get("title"),
        "sentence_patterns": [
            item.get("pattern")
            for item in lesson_data.get("sentence_patterns", [])
            if isinstance(item, dict)
        ],
        "checklist": lesson_data.get("feynman_prompt", {}).get("checklist", []),
    }
    prompt = (
        "Evaluate a learner's short Feynman explanation for a language lesson. "
        "Return JSON only with keys: summary, strengths, missing_points, corrections, "
        "suggested_simple_explanation, related_weak_items, score. "
        f"Lesson summary: {lesson_summary}. "
        f"Learner explanation: {explanation}"
    )
    response = await ollama_client.generate(
        prompt=prompt,
        system_prompt="You are a strict but supportive language-learning coach. Output JSON only.",
        format="json",
        timeout_profile="structured_json",
        use_cache=False,
    )
    if not response.get("success"):
        return None
    parsed = ollama_client.parse_json_response(str(response.get("response", "")))
    if not isinstance(parsed, dict):
        return None
    try:
        return FeynmanFeedback(**parsed)
    except Exception:
        return None


def _build_feynman_fallback_feedback(
    *,
    language: str,
    explanation: str,
    lesson_data: Dict[str, Any],
) -> FeynmanFeedback:
    normalized = explanation.lower()
    prompt = lesson_data.get("feynman_prompt", {}) if isinstance(lesson_data.get("feynman_prompt"), dict) else {}
    checklist = [str(item) for item in prompt.get("checklist", []) if str(item).strip()]
    vocab_words = [
        str(item.get("word", "")).strip()
        for item in lesson_data.get("vocabulary", [])
        if isinstance(item, dict) and str(item.get("word", "")).strip()
    ]
    grammar_title = str(lesson_data.get("grammar", {}).get("title", "")).strip()
    sentence_patterns = [
        str(item.get("pattern", "")).strip()
        for item in lesson_data.get("sentence_patterns", [])
        if isinstance(item, dict) and str(item.get("pattern", "")).strip()
    ]

    mentioned_vocab = [word for word in vocab_words if word.lower() in normalized]
    mentioned_patterns = [pattern for pattern in sentence_patterns if pattern.lower() in normalized]
    grammar_mentioned = bool(grammar_title and grammar_title.lower() in normalized)
    checklist_hits = sum(1 for item in checklist if _keyword_overlap(normalized, item))
    word_bonus = 1 if len(explanation.split()) >= 25 else 0

    score = min(
        100,
        25
        + min(len(mentioned_vocab), 3) * 12
        + min(len(mentioned_patterns), 2) * 12
        + (12 if grammar_mentioned else 0)
        + checklist_hits * 8
        + word_bonus * 7,
    )

    strengths: List[str] = []
    missing_points: List[str] = []
    corrections: List[str] = []
    related_weak_items: List[str] = []

    if mentioned_vocab:
        strengths.append(f"Used lesson vocabulary: {', '.join(mentioned_vocab[:3])}.")
    else:
        missing_points.append("Use at least one target vocabulary word from the lesson.")
        related_weak_items.extend(vocab_words[:2])

    if grammar_mentioned:
        strengths.append(f"Referenced the grammar focus: {grammar_title}.")
    elif grammar_title:
        missing_points.append(f"Explain the grammar point more directly: {grammar_title}.")
        related_weak_items.append(grammar_title)

    if mentioned_patterns:
        strengths.append(f"Reused sentence patterns: {', '.join(mentioned_patterns[:2])}.")
    elif sentence_patterns:
        missing_points.append("Reuse one of the sentence patterns in your own example.")
        related_weak_items.extend(sentence_patterns[:1])

    if checklist and checklist_hits >= max(1, len(checklist) // 2):
        strengths.append("Covered several items from the Feynman checklist.")
    elif checklist:
        missing_points.append("Cover more of the lesson checklist in the explanation.")

    if len(explanation.split()) < 12:
        corrections.append("The explanation is very short; add one simple example and one reason.")
    if not strengths:
        strengths.append("You attempted a personal explanation instead of copying the lesson.")
    if not corrections:
        corrections.append("Keep the explanation simple, but connect vocabulary, grammar, and one example.")

    suggested_simple_explanation = _build_simple_explanation(
        language=language,
        vocab_words=vocab_words,
        grammar_title=grammar_title,
        sentence_patterns=sentence_patterns,
    )
    summary = (
        "Strong coverage with room for a clearer teaching-style explanation."
        if score >= 70
        else "Partial understanding shown; the next step is to connect the key vocabulary and pattern more clearly."
    )

    return FeynmanFeedback(
        summary=summary,
        strengths=strengths,
        missing_points=missing_points,
        corrections=corrections,
        suggested_simple_explanation=suggested_simple_explanation,
        related_weak_items=list(dict.fromkeys(item for item in related_weak_items if item)),
        score=score,
    )


def _build_simple_explanation(
    *,
    language: str,
    vocab_words: List[str],
    grammar_title: str,
    sentence_patterns: List[str],
) -> str:
    if language == "JP":
        vocab = vocab_words[0] if vocab_words else "言葉"
        pattern = sentence_patterns[0] if sentence_patterns else "文型"
        grammar = grammar_title or "文法"
        return f"このレッスンでは「{vocab}」を使って、{grammar} と {pattern} を練習します。短い例を言ってから、自分の言葉で説明します。"

    vocab = vocab_words[0] if vocab_words else "word"
    pattern = sentence_patterns[0] if sentence_patterns else "sentence pattern"
    grammar = grammar_title or "grammar point"
    return f"In this lesson, I use {vocab} to practice the {grammar} and the pattern {pattern}. Then I explain it again with one simple personal example."


def _keyword_overlap(normalized_explanation: str, checklist_item: str) -> bool:
    for token in str(checklist_item).lower().replace(".", " ").replace(",", " ").split():
        if len(token) >= 4 and token in normalized_explanation:
            return True
    return False


def _mark_missing_items_from_feedback(
    *,
    user_id: str,
    language: str,
    feedback: FeynmanFeedback,
) -> None:
    for item_key in feedback.related_weak_items:
        matched = None
        for item_type in ("vocabulary", "grammar", "sentence_pattern"):
            matched = db.get_learning_item_by_key(
                user_id=user_id,
                item_type=item_type,
                item_key=item_key,
                language=language,
            )
            if matched:
                break
        if not matched:
            continue
        db.record_learning_item_review(
            user_id=user_id,
            item_id=str(matched["id"]),
            rating=1,
            correct=False,
            source="feynman_feedback",
        )
