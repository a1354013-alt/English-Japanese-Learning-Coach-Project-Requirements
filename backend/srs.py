"""
Spaced Repetition System (SRS) implementation using SM-2 algorithm
"""
from datetime import datetime, timedelta
from typing import Dict, Any

class SM2:
    """SuperMemo-2 algorithm implementation"""
    
    @staticmethod
    def calculate(
        quality: int,
        prev_interval: int,
        prev_ease_factor: float,
        repetition: int
    ) -> Dict[str, Any]:
        """
        Calculate next review interval and ease factor
        
        Args:
            quality: 0-5 (0: total blackout, 5: perfect response)
            prev_interval: previous interval in days
            prev_ease_factor: previous ease factor
            repetition: number of successful repetitions
            
        Returns:
            Dict with new interval, ease factor, and repetition count
        """
        # Quality below 3 means the item was forgotten
        if quality < 3:
            return {
                "interval": 1,
                "ease_factor": prev_ease_factor,
                "repetition": 0,
                "next_review": datetime.now() + timedelta(days=1)
            }
        
        # Calculate new ease factor
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ease_factor = prev_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if new_ease_factor < 1.3:
            new_ease_factor = 1.3
            
        # Calculate new interval
        if repetition == 0:
            new_interval = 1
        elif repetition == 1:
            new_interval = 6
        else:
            new_interval = round(prev_interval * new_ease_factor)
            
        return {
            "interval": new_interval,
            "ease_factor": new_ease_factor,
            "repetition": repetition + 1,
            "next_review": datetime.now() + timedelta(days=new_interval)
        }

srs_engine = SM2()
