"""Data models for Language Coach application."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any, Dict
from datetime import datetime
from uuid import uuid4
from enum import Enum


# ============ Vocabulary Models ============
class VocabularyItem(BaseModel):
    """Single vocabulary item"""
    word: str
    reading: Optional[str] = None  # For Japanese (hiragana/katakana)
    phonetic: Optional[str] = None  # For English (IPA)
    definition_zh: str
    example_sentence: str
    example_translation: str
    synonyms: Optional[List[str]] = None
    antonyms: Optional[List[str]] = None
    # SRS Fields
    srs_level: int = 0
    next_review: Optional[datetime] = None
    ease_factor: float = 2.5
    interval: int = 0


# ============ Grammar Models ============
class GrammarExample(BaseModel):
    """Grammar example sentence"""
    sentence: str
    translation: str


class GrammarExercise(BaseModel):
    """Grammar practice exercise"""
    question: str
    options: Optional[List[str]] = None
    correct_answer: str  # Can be index as string or text answer
    explanation: str
    exercise_type: Literal["multiple_choice", "cloze", "scramble", "dictation"] = "multiple_choice"
    scrambled_words: Optional[List[str]] = None
    audio_url: Optional[str] = None


class GrammarSection(BaseModel):
    """Grammar section with examples and exercises"""
    title: str
    explanation: str
    examples: List[GrammarExample]
    exercises: List[GrammarExercise]


# ============ Reading Models ============
class ReadingQuestion(BaseModel):
    """Reading comprehension question"""
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class ReadingSection(BaseModel):
    """Reading comprehension section"""
    title: str
    content: str
    word_count: int
    questions: List[ReadingQuestion]


# ============ Dialogue Models ============
class DialogueLine(BaseModel):
    """Single line in a dialogue"""
    speaker: str
    text: str
    translation: str


class DialogueAlternative(BaseModel):
    """Alternative expression for dialogue"""
    original: str
    alternative: str
    context: str


class DialogueSection(BaseModel):
    """Dialogue practice section"""
    scenario: str
    context: str
    dialogue: List[DialogueLine]
    alternatives: List[DialogueAlternative]


# ============ Lesson Models ============
class LessonMetadata(BaseModel):
    """Metadata for a lesson"""
    lesson_id: str = Field(default_factory=lambda: str(uuid4()))
    language: Literal["EN", "JP"]
    level: str  # CEFR (A1-C2) for EN, JLPT (N5-N1) for JP
    topic: str
    generated_at: datetime = Field(default_factory=datetime.now)
    estimated_duration_minutes: int
    key_points: List[str]


class Lesson(BaseModel):
    """Complete lesson structure"""
    metadata: LessonMetadata
    vocabulary: List[VocabularyItem]
    grammar: GrammarSection
    reading: ReadingSection
    dialogue: DialogueSection
    tts_scripts: Optional[List[dict]] = None  # For future TTS integration
    evidence: Optional[List[Dict[str, Any]]] = None  # RAG evidence sources


# ============ Stability & Tracking Models ============
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FALLBACK_SUCCESS = "fallback_success"
    FAILED = "failed"
    RETRIED = "retried"

class GenerationTask(BaseModel):
    task_id: str
    user_id: str
    status: TaskStatus
    model_used: str
    duration_ms: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

class ErrorType(str, Enum):
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    COMPREHENSION = "comprehension"

# ============ RPG & Gamification Models ============
class Achievement(BaseModel):
    """User achievement/medal"""
    id: str
    title: str
    description: str
    icon: str
    unlocked_at: datetime
    rarity: Literal["common", "rare", "epic", "legendary"] = "common"

class WordCard(BaseModel):
    """Collectible vocabulary card"""
    word: str
    rarity: Literal["C", "B", "A", "S", "SS"]
    collected_at: datetime
    language: str

class UserRPGStats(BaseModel):
    """RPG-style user statistics"""
    level: int = 1
    current_xp: int = 0
    next_level_xp: int = 100
    total_xp: int = 0
    avatar_url: str = "https://api.dicebear.com/7.x/avataaars/svg?seed=Manus"
    title: str = "Beginner Adventurer"
    unlocked_skills: List[str] = Field(default_factory=list)
    achievements: List[Achievement] = Field(default_factory=list)
    word_cards: List[WordCard] = Field(default_factory=list)
    streak_days: int = 0
    difficulty_mode: str = "normal" # easy, normal, hardcore
    is_onboarded: bool = False
    error_distribution: Dict[str, int] = Field(default_factory=lambda: {
        "spelling": 0,
        "grammar": 0,
        "vocabulary": 0,
        "comprehension": 0
    })

# ============ Progress Models ============
class LanguageProgress(BaseModel):
    """Progress tracking for a specific language"""
    language: Literal["EN", "JP"]
    current_level: str
    target_level: str
    completed_lessons: int
    total_exercises: int
    correct_exercises: int
    accuracy_rate: float = 0.0
    last_study_date: Optional[datetime] = None


class UserProgress(BaseModel):
    """Overall user progress"""
    user_id: str = "default_user"
    english_progress: LanguageProgress
    japanese_progress: LanguageProgress
    rpg_stats: UserRPGStats = Field(default_factory=UserRPGStats)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============ Review Models ============
class ReviewAnswer(BaseModel):
    """User's answer to an exercise"""
    lesson_id: str
    exercise_type: Literal["grammar", "reading"]  # Restricted to valid exercise types
    question_index: int
    user_answer: str
    correct_answer: str


class IncorrectItem(BaseModel):
    """Incorrect item in review result"""
    question: str
    user_answer: str
    correct_answer: str
    explanation: str


class ReviewResult(BaseModel):
    """Result of exercise review"""
    total_questions: int
    correct_count: int
    accuracy_rate: float
    incorrect_items: List[IncorrectItem]


# ============ Wrong Answer Notebook Models ============
WrongAnswerStatus = Literal["active", "mastered"]


class WrongAnswerCreate(BaseModel):
    language: str
    question_type: str
    question: str
    user_answer: str
    correct_answer: str
    source_lesson_id: Optional[str] = None


class WrongAnswerUpdate(BaseModel):
    status: WrongAnswerStatus


class WrongAnswerRetryRequest(BaseModel):
    user_answer: str


class WrongAnswer(BaseModel):
    id: int
    user_id: str
    language: str
    question_type: str
    question: str
    user_answer: str
    correct_answer: str
    source_lesson_id: Optional[str] = None
    status: WrongAnswerStatus
    wrong_count: int = 1
    created_at: datetime
    updated_at: datetime


# ============ Daily Learning Streak Models ============
class StreakInfo(BaseModel):
    current_streak: int
    longest_streak: int
    last_active_date: Optional[str] = None  # YYYY-MM-DD
    today_completed: bool


# ============ Writing Assistant Models ============
class WritingAnalysis(BaseModel):
    """AI analysis of user writing"""
    original_text: str
    corrected_text: str
    grammar_score: int  # 0-100
    vocabulary_score: int  # 0-100
    style_score: int  # 0-100
    overall_score: int  # 0-100
    estimated_level: str  # CEFR or JLPT
    corrections: List[Dict[str, str]]  # List of {original, corrected, explanation, type}
    suggestions: List[str]
    feedback: str

class WritingSubmission(BaseModel):
    """User writing submission"""
    language: Literal["EN", "JP"]
    text: str
    topic: Optional[str] = None
    target_level: Optional[str] = None

# ============ Study Plan Models ============
class StudyMilestone(BaseModel):
    """A milestone in the study plan"""
    title: str
    description: str
    target_date: datetime
    required_skills: List[str]
    is_completed: bool = False

class StudyPlan(BaseModel):
    """AI generated study plan"""
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    target_goal: str  # e.g., "TOEIC 800", "JLPT N2"
    language: Literal["EN", "JP"]
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: datetime
    milestones: List[StudyMilestone]
    daily_commitment_minutes: int
    focus_areas: List[str]
    generated_at: datetime = Field(default_factory=datetime.now)

# ============ API Request Models ============
class GenerateLessonRequest(BaseModel):
    """Request to generate a new lesson"""
    language: Literal["EN", "JP"]
    topic: Optional[str] = None
    difficulty: Optional[str] = None  # If not provided, use current progress level
    interest_context: Optional[str] = None  # User uploaded article or interest


class LessonQueryParams(BaseModel):
    """Query parameters for lesson listing"""
    language: Optional[Literal["EN", "JP"]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    level: Optional[str] = None
    topic: Optional[str] = None
    limit: int = 20
    offset: int = 0
