"""Scheduler for automatic lesson generation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Awaitable

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from database import db
from lesson_generator import lesson_generator

logger = logging.getLogger(__name__)


class LessonScheduler:
    """Scheduler for automatic daily lesson generation."""

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(settings.timezone)

    def _run_async_task(self, coro: Awaitable[None]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            try:
                future.result(timeout=300)
            except Exception as err:
                logger.exception("scheduler_async_task_failed", extra={"error": str(err)})
            return

        loop.run_until_complete(coro)

    async def _generate_daily_lessons_async(self) -> None:
        logger.info("daily_lesson_generation_started", extra={"started_at": datetime.now().isoformat()})

        user_id = settings.default_user_id
        today_en = db.get_today_lesson(user_id, "EN")
        today_jp = db.get_today_lesson(user_id, "JP")

        if not today_en:
            logger.info("daily_lesson_generation_language_started", extra={"language": "EN"})
            try:
                await lesson_generator.generate_lesson(language="EN", user_id=user_id)
                logger.info("daily_lesson_generation_language_succeeded", extra={"language": "EN"})
            except Exception as err:
                logger.exception("daily_lesson_generation_language_failed", extra={"language": "EN", "error": str(err)})
        else:
            logger.info("daily_lesson_already_exists", extra={"language": "EN"})

        if not today_jp:
            logger.info("daily_lesson_generation_language_started", extra={"language": "JP"})
            try:
                await lesson_generator.generate_lesson(language="JP", user_id=user_id)
                logger.info("daily_lesson_generation_language_succeeded", extra={"language": "JP"})
            except Exception as err:
                logger.exception("daily_lesson_generation_language_failed", extra={"language": "JP", "error": str(err)})
        else:
            logger.info("daily_lesson_already_exists", extra={"language": "JP"})

        logger.info("daily_lesson_generation_completed", extra={"finished_at": datetime.now().isoformat()})

    def generate_daily_lessons(self) -> None:
        self._run_async_task(self._generate_daily_lessons_async())

    def start(self) -> None:
        try:
            hour, minute = map(int, settings.auto_generate_time.split(":"))
        except ValueError:
            logger.warning("scheduler_invalid_auto_generate_time", extra={"value": settings.auto_generate_time})
            hour, minute = 7, 30

        self.scheduler.add_job(
            self.generate_daily_lessons,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
            id="daily_lesson_generation",
            name="Generate daily lessons",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            "scheduler_started",
            extra={"auto_generate_time": settings.auto_generate_time, "timezone": settings.timezone},
        )

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("scheduler_stopped")

    def trigger_now(self) -> None:
        self.generate_daily_lessons()


lesson_scheduler = LessonScheduler()
