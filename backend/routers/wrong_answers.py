"""Wrong Answer Notebook CRUD + retry API."""

from fastapi import APIRouter, Depends, HTTPException, Query

from config import settings
from database import db
from models import (
    WrongAnswer,
    WrongAnswerCreate,
    WrongAnswerRetryRequest,
    WrongAnswerStatus,
    WrongAnswerUpdate,
)
from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["wrong-answers"])


@router.get("/wrong-answers", response_model=dict)
async def list_wrong_answers(
    user_id: str = Depends(require_demo_user_id),
    status: WrongAnswerStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    items = db.list_wrong_answers(user_id=user_id, status=status, limit=limit, offset=offset)
    return {"success": True, "count": len(items), "items": [WrongAnswer(**item).model_dump(mode="json") for item in items]}


@router.post("/wrong-answers", response_model=dict)
async def create_wrong_answer(
    payload: WrongAnswerCreate,
    user_id: str = Depends(require_demo_user_id),
):
    item = db.upsert_wrong_answer(
        user_id=user_id,
        language=payload.language,
        question_type=payload.question_type,
        question=payload.question,
        user_answer=payload.user_answer,
        correct_answer=payload.correct_answer,
        source_lesson_id=payload.source_lesson_id,
    )
    return {"success": True, "item": WrongAnswer(**item).model_dump(mode="json")}


@router.patch("/wrong-answers/{wrong_answer_id}", response_model=dict)
async def update_wrong_answer(
    wrong_answer_id: int,
    payload: WrongAnswerUpdate,
    user_id: str = Depends(require_demo_user_id),
):
    item = db.update_wrong_answer_status(user_id=user_id, wrong_answer_id=wrong_answer_id, status=payload.status)
    if not item:
        raise HTTPException(status_code=404, detail="Wrong answer not found")
    return {"success": True, "item": WrongAnswer(**item).model_dump(mode="json")}


@router.delete("/wrong-answers/{wrong_answer_id}", response_model=dict)
async def delete_wrong_answer(
    wrong_answer_id: int,
    user_id: str = Depends(require_demo_user_id),
):
    ok = db.delete_wrong_answer(user_id=user_id, wrong_answer_id=wrong_answer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Wrong answer not found")
    return {"success": True}


@router.post("/wrong-answers/{wrong_answer_id}/retry", response_model=dict)
async def retry_wrong_answer(
    wrong_answer_id: int,
    payload: WrongAnswerRetryRequest,
    user_id: str = Depends(require_demo_user_id),
):
    db.record_learning_activity(user_id=user_id, activity_type="retry_wrong_answer")
    correct, item = db.retry_wrong_answer(user_id=user_id, wrong_answer_id=wrong_answer_id, user_answer=payload.user_answer)
    if not item:
        raise HTTPException(status_code=404, detail="Wrong answer not found")
    return {"success": True, "correct": correct, "item": WrongAnswer(**item).model_dump(mode="json")}

