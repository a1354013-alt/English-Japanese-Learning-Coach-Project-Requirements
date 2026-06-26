"""Timezone-aware time helpers used by backend business logic."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from config import settings


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def local_today() -> date:
    return local_now().date()
