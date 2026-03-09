"""
Scheduler for automatic lesson generation
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz

from config import settings
from lesson_generator import lesson_generator
from database import db


class LessonScheduler:
    """Scheduler for automatic daily lesson generation"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(settings.timezone)
    
    def generate_daily_lessons(self):
        """Generate daily lessons for both English and Japanese"""
        print(f"\n[{datetime.now()}] Starting daily lesson generation...")
        
        # Check if lessons already generated today
        today_en = db.get_today_lesson("EN")
        today_jp = db.get_today_lesson("JP")
        
        # Generate English lesson if not exists
        if not today_en:
            print("Generating English lesson...")
            try:
                lesson_generator.generate_lesson(language="EN")
                print("✓ English lesson generated successfully")
            except Exception as e:
                print(f"✗ Failed to generate English lesson: {e}")
        else:
            print("English lesson already exists for today")
        
        # Generate Japanese lesson if not exists
        if not today_jp:
            print("Generating Japanese lesson...")
            try:
                lesson_generator.generate_lesson(language="JP")
                print("✓ Japanese lesson generated successfully")
            except Exception as e:
                print(f"✗ Failed to generate Japanese lesson: {e}")
        else:
            print("Japanese lesson already exists for today")
        
        print(f"[{datetime.now()}] Daily lesson generation completed\n")
    
    def start(self):
        """Start the scheduler"""
        # Parse time from settings (format: "HH:MM")
        hour, minute = map(int, settings.auto_generate_time.split(':'))
        
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
        self.scheduler.shutdown()
        print("Scheduler stopped")
    
    def trigger_now(self):
        """Manually trigger lesson generation"""
        self.generate_daily_lessons()


# Global scheduler instance
lesson_scheduler = LessonScheduler()
