from datetime import date, timedelta

import database as database_module
import gamification_engine as gamification_module
import services.streak_service as streak_service_module
from database import Database
from models import UserRPGStats


def test_check_achievements_does_not_overwrite_streak_stats_and_is_idempotent(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(streak_service_module.database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)

    user_id = "u1"
    progress = test_db.get_progress(user_id)
    progress["english_progress"]["completed_lessons"] = 5
    progress["english_progress"]["total_exercises"] = 5
    progress["english_progress"]["correct_exercises"] = 5
    progress["english_progress"]["accuracy_rate"] = 100.0
    progress["japanese_progress"]["accuracy_rate"] = 100.0
    stats = UserRPGStats(total_xp=123, current_xp=23, streak_days=0)
    progress["rpg_stats"] = stats.model_dump(mode="json")
    test_db.save_progress(progress)

    today = date.fromisoformat(test_db._local_date_str())
    for offset in range(7):
        test_db.record_learning_activity(
            user_id=user_id,
            activity_type="review",
            activity_date=(today - timedelta(days=offset)).isoformat(),
        )

    unlocked = gamification_module.gamification_engine.check_achievements(user_id)
    saved = UserRPGStats(**test_db.get_rpg_stats(user_id))

    unlocked_ids = {achievement.id for achievement in unlocked}
    saved_ids = {achievement.id for achievement in saved.achievements}
    assert {"week_streak", "perfectionist"}.issubset(unlocked_ids)
    assert {"week_streak", "perfectionist"}.issubset(saved_ids)
    assert saved.streak_days == 7
    assert saved.total_xp == 123
    assert saved.current_xp == 23

    second = gamification_module.gamification_engine.check_achievements(user_id)
    saved_again = UserRPGStats(**test_db.get_rpg_stats(user_id))
    assert second == []
    assert len(saved_again.achievements) == len(saved.achievements)
    assert saved_again.streak_days == 7
