"""
Scheduler for automatic lesson generation
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import asyncio

from config import settings
from lesson_generator import lesson_generator
from database import db

logger = logging.getLogger(__name__)


class LessonScheduler:
    """Scheduler for automatic daily lesson generation"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(settings.timezone)
    
    def _run_async_task(self, coro):
        """Helper to run async coroutine in a synchronous scheduler (P1 Fix)"""
        try:
            # In FastAPI context, get the running loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one (for standalone usage)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If the loop is already running (e.g. in FastAPI), use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            # Wait for completion with timeout to avoid blocking indefinitely
            try:
                future.result(timeout=300)  # 5 minute timeout
            except Exception as e:
                logger.error(f"Async task failed in scheduler: {e}")
        else:
            loop.run_until_complete(coro)

    async def _generate_daily_lessons_async(self):
        """Internal async implementation of daily lesson generation"""
        print(f"\n[{datetime.now()}] Starting daily lesson generation...")
        
        # Check if lessons already generated today
        today_en = db.get_today_lesson("EN")
        today_jp = db.get_today_lesson("JP")
        
        # Generate English lesson if not exists
        if not today_en:
            print("Generating English lesson...")
            try:
                await lesson_generator.generate_lesson(language="EN")
                print("✓ English lesson generated successfully")
            except Exception as e:
                print(f"✗ Failed to generate English lesson: {e}")
        else:
            print("English lesson already exists for today")
        
        # Generate Japanese lesson if not exists
        if not today_jp:
            print("Generating Japanese lesson...")
            try:
                await lesson_generator.generate_lesson(language="JP")
                print("✓ Japanese lesson generated successfully")
            except Exception as e:
                print(f"✗ Failed to generate Japanese lesson: {e}")
        else:
            print("Japanese lesson already exists for today")
        
        print(f"[{datetime.now()}] Daily lesson generation completed\n")

    def generate_daily_lessons(self):
        """Synchronous wrapper for the scheduler"""
        self._run_async_task(self._generate_daily_lessons_async())
    
    def start(self):
        """Start the scheduler"""
        # Parse time from settings (format: "HH:MM")
        try:
            hour, minute = map(int, settings.auto_generate_time.split(':'))
        except ValueError:
            print(f"Invalid auto_generate_time format: {settings.auto_generate_time}. Using default 07:30.")
            hour, minute = 7, 30
        
        # Add daily job
        self.scheduler.add_job(
            self.generate_daily_lessons,
            trigger=CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.timezone
            ),
            id='daily_lesson_generation',
            name='Generate daily lessons',
            replace_existing=True
        )
        
        self.scheduler.start()
        print(f"Scheduler started: Daily lessons will be generated at {settings.auto_generate_time} {settings.timezone}")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Scheduler stopped")
    
    def trigger_now(self):
        """Manually trigger lesson generation"""
        self.generate_daily_lessons()


# Global scheduler instance
lesson_scheduler = LessonScheduler()
