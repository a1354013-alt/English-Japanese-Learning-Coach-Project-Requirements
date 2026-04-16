"""
Gamification Engine for Language Coach
Handles XP calculation, leveling, and achievements
"""
from datetime import datetime, time
from typing import List, Dict, Any, Optional
from models import UserRPGStats, Achievement, WordCard
from database import db

class GamificationEngine:
    """Logic for RPG-style progression"""
    
    XP_PER_LESSON = 50
    XP_PER_CORRECT_ANSWER = 10
    XP_PER_STREAK_DAY = 20
    
    def calculate_next_level_xp(self, level: int) -> int:
        """Calculate XP required for next level using a simple curve"""
        return int(100 * (level ** 1.5))

    def add_xp(self, user_id: str, amount: int) -> Dict[str, Any]:
        """Add XP to user and handle leveling up"""
        # P1 Fix: Use get_rpg_stats/save_rpg_stats for consistency
        rpg_stats_data = db.get_rpg_stats(user_id) or {}
        rpg_stats = UserRPGStats(**rpg_stats_data)
        
        rpg_stats.current_xp += amount
        rpg_stats.total_xp += amount
        
        leveled_up = False
        while rpg_stats.current_xp >= rpg_stats.next_level_xp:
            rpg_stats.current_xp -= rpg_stats.next_level_xp
            rpg_stats.level += 1
            rpg_stats.next_level_xp = self.calculate_next_level_xp(rpg_stats.level)
            leveled_up = True
            
            # Unlock skills based on level
            self._check_skill_unlocks(rpg_stats)
            
        # Update RPG stats in DB
        db.save_rpg_stats(user_id, rpg_stats.model_dump(mode='json'))
        
        return {
            "leveled_up": leveled_up,
            "new_level": rpg_stats.level,
            "xp_added": amount,
            "current_xp": rpg_stats.current_xp,
            "next_level_xp": rpg_stats.next_level_xp
        }

    def _check_skill_unlocks(self, rpg_stats: UserRPGStats):
        """Unlock new 'skills' (content types) based on level"""
        unlocks = {
            5: "Advanced Grammar",
            10: "Business Communication",
            15: "Slang & Idioms",
            20: "Literature Analysis"
        }
        
        for level, skill in unlocks.items():
            if rpg_stats.level >= level and skill not in rpg_stats.unlocked_skills:
                rpg_stats.unlocked_skills.append(skill)
                rpg_stats.title = f"{skill} Apprentice"

    def check_achievements(self, user_id: str) -> List[Achievement]:
        """Check and unlock achievements based on user activity"""
        progress = db.get_progress(user_id)
        if not progress:
            return []
            
        rpg_stats_data = db.get_rpg_stats(user_id) or {}
        rpg_stats = UserRPGStats(**rpg_stats_data)
        unlocked_now = []
        
        # 1. Early Bird Achievement (Study before 7:30 AM)
        now = datetime.now()
        if now.time() < time(7, 30):
            self._unlock_achievement(rpg_stats, "early_bird", "Early Bird", "Study before 7:30 AM", "🌅", "rare", unlocked_now)
            
        # 2. Streak Achievements
        if rpg_stats.streak_days >= 7:
            self._unlock_achievement(rpg_stats, "week_streak", "Week Warrior", "Maintain a 7-day streak", "🔥", "epic", unlocked_now)
            
        # 3. Accuracy Achievement (P1 Fix: Accuracy is 0-100 in progress)
        total_accuracy = (progress['english_progress']['accuracy_rate'] + progress['japanese_progress']['accuracy_rate']) / 2
        if total_accuracy >= 90 and (progress['english_progress']['completed_lessons'] + progress['japanese_progress']['completed_lessons']) >= 5:
            self._unlock_achievement(rpg_stats, "perfectionist", "Perfectionist", "Maintain >90% accuracy over 5 lessons", "🎯", "legendary", unlocked_now)

        if unlocked_now:
            db.save_rpg_stats(user_id, rpg_stats.model_dump(mode='json'))
            
        return unlocked_now

    def _unlock_achievement(self, rpg_stats: UserRPGStats, id: str, title: str, desc: str, icon: str, rarity: str, unlocked_list: list):
        """Helper to unlock an achievement if not already unlocked"""
        if not any(a.id == id for a in rpg_stats.achievements):
            new_achievement = Achievement(
                id=id, title=title, description=desc, icon=icon, 
                unlocked_at=datetime.now(), rarity=rarity
            )
            rpg_stats.achievements.append(new_achievement)
            unlocked_list.append(new_achievement)

    def check_and_unlock_achievements(self, user_id: str) -> List[Achievement]:
        """Public method to check and unlock achievements (called from routers)"""
        return self.check_achievements(user_id)

    def collect_word_cards(self, user_id: str, words: List[str], language: str) -> List[WordCard]:
        """Convert learned words into collectible cards with rarity"""
        rpg_stats_data = db.get_rpg_stats(user_id) or {}
        rpg_stats = UserRPGStats(**rpg_stats_data)
        new_cards = []
        
        import random
        rarities = ["C", "B", "A", "S", "SS"]
        weights = [0.5, 0.3, 0.15, 0.04, 0.01] # Rarity distribution
        
        for word in words:
            # Check if already collected
            if any(card.word == word and card.language == language for card in rpg_stats.word_cards):
                continue
                
            rarity = random.choices(rarities, weights=weights)[0]
            new_card = WordCard(
                word=word,
                rarity=rarity,
                collected_at=datetime.now(),
                language=language
            )
            rpg_stats.word_cards.append(new_card)
            new_cards.append(new_card)
            
        if new_cards:
            db.save_rpg_stats(user_id, rpg_stats.model_dump(mode='json'))
            
        return new_cards

# Global instance
gamification_engine = GamificationEngine()
