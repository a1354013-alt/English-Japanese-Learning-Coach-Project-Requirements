"""Data models for Language Coach application."""
from pydantic import BaseModel, Field, StrictInt, StrictStr
from typing import List, Optional, Literal, Any, Dict, TypeAlias
from datetime import datetime
from uuid import uuid4
from enum import Enum

LanguageCode: TypeAlias = Literal["EN", "JP"]


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
class LessonEvidence(BaseModel):
    material_id: str
    doc_id: Optional[str] = None
    text: str = ""
    source: str
    title: str
    language: Optional[LanguageCode] = None
    source_type: Optional[str] = None
    uploaded_at: Optional[str] = None
    total_chunks: int = 1
    chunk_index: int = 0


class LessonMetadata(BaseModel):
    """Metadata for a lesson"""
    lesson_id: str = Field(default_factory=lambda: str(uuid4()))
    language: LanguageCode
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
    tts_scripts: Optional[List[Dict[str, Any]]] = None  # For future TTS integration
    evidence: Optional[List[LessonEvidence]] = None  # RAG evidence sources
    gamification: Optional["LessonGamification"] = None


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
    language: LanguageCode
    reading: Optional[str] = None
    phonetic: Optional[str] = None
    definition_zh: Optional[str] = None
    example_sentence: Optional[str] = None
    example_translation: Optional[str] = None

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
    language: LanguageCode
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
    lesson_id: StrictStr
    exercise_type: Literal["grammar", "reading"]  # Restricted to valid exercise types
    question_index: StrictInt
    user_answer: StrictStr
    correct_answer: StrictStr


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
    language: LanguageCode
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
    language: LanguageCode
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
class WritingCorrection(BaseModel):
    original: str
    corrected: str
    explanation: str
    type: str


class WritingAnalysis(BaseModel):
    """AI analysis of user writing"""
    original_text: str
    corrected_text: str
    grammar_score: int  # 0-100
    vocabulary_score: int  # 0-100
    style_score: int  # 0-100
    overall_score: int  # 0-100
    estimated_level: str  # CEFR or JLPT
    corrections: List[WritingCorrection]
    suggestions: List[str]
    feedback: str

class WritingSubmission(BaseModel):
    """User writing submission"""
    language: LanguageCode
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
    language: LanguageCode
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: datetime
    milestones: List[StudyMilestone]
    daily_commitment_minutes: int
    focus_areas: List[str]
    generated_at: datetime = Field(default_factory=datetime.now)

# ============ API Request Models ============
class GenerateLessonRequest(BaseModel):
    """Request to generate a new lesson"""
    language: LanguageCode
    topic: Optional[str] = None
    difficulty: Optional[str] = None  # If not provided, use current progress level
    interest_context: Optional[str] = None  # User uploaded article or interest


class LessonQueryParams(BaseModel):
    """Query parameters for lesson listing"""
    language: Optional[LanguageCode] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    level: Optional[str] = None
    topic: Optional[str] = None
    limit: int = 20
    offset: int = 0


# ============ API Response Models ============
class ApiErrorPayload(BaseModel):
    error: bool = True
    message: str
    code: str
    detail: Optional[Any] = None


class SuccessResponse(BaseModel):
    success: bool = True


class MessageResponse(SuccessResponse):
    message: str


class LessonGamification(BaseModel):
    xp_added: int
    leveled_up: bool = False
    new_cards: List[WordCard] = Field(default_factory=list)


class ReviewGamification(BaseModel):
    xp_added: int
    leveled_up: bool = False


class GeneratedLessonResponse(SuccessResponse):
    lesson: Lesson


class LessonListItem(BaseModel):
    lesson_id: str
    user_id: str
    language: LanguageCode
    level: str
    topic: str
    generated_at: datetime
    estimated_duration_minutes: Optional[int] = None
    key_points: List[str] | str | None = None
    file_path: str
    created_at: Optional[datetime] = None


class LessonListResponse(SuccessResponse):
    count: int
    lessons: List[LessonListItem]


class LessonDetailResponse(SuccessResponse):
    lesson: Lesson


class TodayLessonResponse(SuccessResponse):
    lesson: Optional[Lesson] = None


class ReviewSubmitResponse(SuccessResponse):
    total_questions: int
    correct_count: int
    accuracy_rate: float
    incorrect_items: List[IncorrectItem]
    gamification: ReviewGamification


class SrsDueItem(BaseModel):
    word: str
    language: LanguageCode
    definition_zh: Optional[str] = None
    next_review: Optional[datetime] = None
    interval: int
    ease_factor: float
    srs_level: int


class SrsDueResponse(SuccessResponse):
    items: List[SrsDueItem]


class TasksResponse(SuccessResponse):
    tasks: List[GenerationTask]


class StreakResponse(SuccessResponse):
    current_streak: int
    longest_streak: int
    last_active_date: Optional[str] = None
    today_completed: bool


class WritingAnalysisResponse(SuccessResponse):
    analysis: WritingAnalysis


class StudyPlanResponse(SuccessResponse):
    plan: StudyPlan


class TtsResponse(SuccessResponse):
    available: bool
    audio_url: Optional[str] = None
    mode: Literal["live", "preview"]
    message: Optional[str] = None


class RagMaterial(BaseModel):
    material_id: str
    doc_id: str
    source: str
    title: str
    language: LanguageCode
    source_type: Optional[str] = None
    uploaded_at: Optional[str] = None
    total_chunks: int = 1
    text: Optional[str] = None


class RagUploadResponse(SuccessResponse):
    doc_id: str


class RagMaterialsResponse(SuccessResponse):
    items: List[RagMaterial]


class ImportedVocabularyItem(BaseModel):
    id: int
    user_id: str
    language: Literal["EN", "JP"]
    word: str
    reading: Optional[str] = None
    definition_zh: str
    example_sentence: Optional[str] = None
    example_translation: Optional[str] = None
    created_at: datetime


class ImportedVocabularyListResponse(SuccessResponse):
    count: int
    items: List[ImportedVocabularyItem]


class ImportExcelResponse(SuccessResponse):
    count: int


class WrongAnswerListResponse(SuccessResponse):
    count: int
    items: List[WrongAnswer]


class WrongAnswerItemResponse(SuccessResponse):
    item: WrongAnswer


class WrongAnswerRetryResponse(SuccessResponse):
    correct: bool
    item: WrongAnswer


class RootResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


class DatabaseHealth(BaseModel):
    configured: bool
    reachable: bool
    ready: bool


class OllamaHealth(BaseModel):
    configured: bool
    small_model: str
    large_model: str
    small_model_ready: bool
    large_model_ready: bool
    ready: bool


class RagHealth(BaseModel):
    configured: bool
    ready: bool
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    api: str
    database: DatabaseHealth
    ollama: OllamaHealth
    rag: RagHealth
    timestamp: datetime


class DemoResetSummary(BaseModel):
    lessons: int
    imported_vocabulary: int
    wrong_answers: int
    today_lesson_id: str


class DemoResetResponse(MessageResponse):
    summary: DemoResetSummary


class ProgressResponse(SuccessResponse):
    progress: UserProgress
    streak: StreakInfo


class AnalyticsHardestWord(BaseModel):
    word: str
    mistakes: int


class AnalyticsWeakestCategory(BaseModel):
    category: str
    active_items: int


class AnalyticsTrendPoint(BaseModel):
    lesson_id: Optional[str] = None
    accuracy_rate: float
    submitted_at: datetime


class AnalyticsPayload(BaseModel):
    total_xp: int
    level: int
    streak: int
    longest_streak: int
    lessons_completed: int
    hardest_words: List[AnalyticsHardestWord]
    weakest_category: Optional[AnalyticsWeakestCategory] = None
    accuracy_trend: List[AnalyticsTrendPoint]
    today_completed: bool


class AnalyticsResponse(SuccessResponse):
    analytics: AnalyticsPayload
