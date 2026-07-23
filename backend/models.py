"""Data models for Language Coach application."""
import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypeAlias
from uuid import uuid4

from learning_session_contract import LearningSessionContractViolation, validate_event_contract
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)
from time_utils import local_now

LanguageCode: TypeAlias = Literal["EN", "JP"]
EnglishLevel: TypeAlias = Literal["A1", "A2", "B1", "B2", "C1"]
JapaneseLevel: TypeAlias = Literal["N5", "N4", "N3", "N2", "N1"]
LearningLevel: TypeAlias = EnglishLevel | JapaneseLevel
DifficultyMode: TypeAlias = Literal["easy", "normal", "hardcore"]
MAX_LEARNING_SESSION_PLANNED_MINUTES = 480
MAX_LEARNING_GOAL_DAILY_MINUTES = 480
MAX_LEARNING_GOAL_WEEKLY_SESSIONS = 28
MAX_LEARNING_GOAL_WEEKLY_MINUTES = 3360
MAX_LEARNING_SESSION_IDEMPOTENCY_KEY_LENGTH = 128
MAX_LEARNING_SESSION_EVENT_ENTITY_ID_LENGTH = 120
MAX_LEARNING_SESSION_NOTE_LENGTH = 500
MAX_LEARNING_SESSION_METADATA_BYTES = 1000
MAX_LEARNING_SESSION_PAGE_SIZE = 100
_IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _validate_level_for_language(language: LanguageCode, level: str) -> str:
    valid_levels = {"A1", "A2", "B1", "B2", "C1"} if language == "EN" else {"N5", "N4", "N3", "N2", "N1"}
    if level not in valid_levels:
        expected = ", ".join(sorted(valid_levels))
        raise ValueError(f"level must be one of {expected} for language {language}")
    return level


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
    part_of_speech: Optional[str] = None
    root: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    word_family: Optional[List[str]] = None
    memory_tip: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
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
    related_vocabulary: List[str] = Field(default_factory=list)
    related_grammar: List[str] = Field(default_factory=list)
    related_sentence_patterns: List[str] = Field(default_factory=list)


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
    related_vocabulary: List[str] = Field(default_factory=list)
    related_grammar: List[str] = Field(default_factory=list)
    related_sentence_patterns: List[str] = Field(default_factory=list)


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
class SentencePattern(BaseModel):
    pattern: str
    meaning_zh: str
    usage_note: str
    examples: List[GrammarExample]


class WordRoot(BaseModel):
    root: str
    meaning_zh: str
    examples: List[str]
    memory_tip: str


class ImmersionSection(BaseModel):
    shadowing_text: List[DialogueLine] = Field(default_factory=list)
    repeat_chunks: List[str] = Field(default_factory=list)
    listening_tips: List[str] = Field(default_factory=list)


class FeynmanPrompt(BaseModel):
    prompt: str = ""
    checklist: List[str] = Field(default_factory=list)


LearningItemType: TypeAlias = Literal["vocabulary", "grammar", "sentence_pattern"]
LearningMasteryState: TypeAlias = Literal["new", "learning", "review", "weak", "mastered"]


def review_rating_is_correct(rating: int) -> bool:
    return rating >= 3


class LearningItemContent(BaseModel):
    item_key: str
    content: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    root: Optional[str] = None
    memory_tip: Optional[str] = None


class LearningItemDue(BaseModel):
    item_id: str
    item_type: LearningItemType
    item_key: str
    language: LanguageCode
    level: Optional[str] = None
    content: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    root: Optional[str] = None
    memory_tip: Optional[str] = None
    mastery_state: LearningMasteryState
    due_at: datetime


class LearningItemDueResponse(BaseModel):
    success: bool = True
    items: List[LearningItemDue]


class LearningItemGroupResponse(BaseModel):
    success: bool = True
    vocabulary: List[LearningItemDue]
    grammar: List[LearningItemDue]
    sentence_pattern: List[LearningItemDue]


class LearningItemReviewRequest(BaseModel):
    item_id: str
    rating: int = Field(ge=0, le=5)
    correct: Optional[bool] = Field(
        default=None,
        description="Deprecated. Correctness is derived from rating and this field is ignored.",
        json_schema_extra={"deprecated": True},
    )
    response_time_ms: Optional[int] = Field(default=None, ge=0)
    source: Literal["lesson_review", "srs_review", "feynman_feedback", "manual"] = "manual"


class LearningItemReviewState(BaseModel):
    success: bool = True
    item_id: str
    interval_days: int
    ease_factor: float
    repetitions: int
    lapses: int
    due_at: datetime
    last_reviewed_at: Optional[datetime] = None
    mastery_state: LearningMasteryState


class FeynmanFeedback(BaseModel):
    summary: str
    strengths: List[str] = Field(default_factory=list)
    missing_points: List[str] = Field(default_factory=list)
    corrections: List[str] = Field(default_factory=list)
    suggested_simple_explanation: str
    related_weak_items: List[str] = Field(default_factory=list)
    score: int = Field(ge=0, le=100)


class FeynmanFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    explanation: str
    language: LanguageCode


class FeynmanFeedbackResponse(BaseModel):
    success: bool = True
    feedback: FeynmanFeedback


class ReviewPlan(BaseModel):
    today: List[str] = Field(default_factory=list)
    next_1_day: List[str] = Field(default_factory=list)
    next_3_days: List[str] = Field(default_factory=list)
    next_7_days: List[str] = Field(default_factory=list)


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
    generated_at: datetime = Field(default_factory=local_now)
    estimated_duration_minutes: int
    key_points: List[str]


class Lesson(BaseModel):
    """Complete lesson structure"""
    metadata: LessonMetadata
    objectives: List[str] = Field(default_factory=list)
    vocabulary: List[VocabularyItem]
    word_roots: List[WordRoot] = Field(default_factory=list)
    sentence_patterns: List[SentencePattern] = Field(default_factory=list)
    grammar: GrammarSection
    reading: ReadingSection
    dialogue: DialogueSection
    immersion: ImmersionSection = Field(default_factory=ImmersionSection)
    feynman_prompt: FeynmanPrompt = Field(default_factory=FeynmanPrompt)
    review_plan: ReviewPlan = Field(default_factory=ReviewPlan)
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
    created_at: datetime = Field(default_factory=local_now)

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
    updated_at: datetime = Field(default_factory=local_now)


# ============ Review Models ============
class ReviewAnswer(BaseModel):
    """User's answer to an exercise"""
    lesson_id: StrictStr
    exercise_type: Literal["grammar", "reading"]  # Restricted to valid exercise types
    question_index: StrictInt
    user_answer: StrictStr
    correct_answer: StrictStr
    client_submission_id: Optional[StrictStr] = Field(
        default=None,
        description="Optional client retry key shared by every answer in one review submission.",
    )


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


# ============ Daily Micro Lesson Models ============
class DiagnosticQuestion(BaseModel):
    question_id: str
    prompt: str
    choices: List[str]
    skill: Literal["subject", "verb", "present_simple"]


class DiagnosticQuestionKey(DiagnosticQuestion):
    question_id: str
    correct_answer: str


class DiagnosticQuestionsResponse(BaseModel):
    success: bool = True
    questions: List[DiagnosticQuestion]


class DiagnosticAnswer(BaseModel):
    question_id: StrictStr
    answer: StrictStr


class DiagnosticSubmitRequest(BaseModel):
    answers: List[DiagnosticAnswer]


class LearningPlan(BaseModel):
    estimated_total_days: int = 90
    current_day: int = 1
    summary_zh: str


class DiagnosticSubmitResponse(BaseModel):
    success: bool = True
    learning_plan: LearningPlan


class MicroVocabularyItem(BaseModel):
    word: str
    phonetic: str
    pronunciation_zh: str
    definition_zh: str
    example_sentence: str
    example_translation: str


class MicroDialogueLine(BaseModel):
    speaker: str
    english: str
    translation_zh: str


class ComicPanel(BaseModel):
    panel: int
    english: str
    translation_zh: str
    scene_prompt: str


class FillBlankQuestion(BaseModel):
    prompt: str
    choices: List[str]
    correct_answer: str
    explanation: str


class MicroLesson(BaseModel):
    lesson_id: str = Field(default_factory=lambda: str(uuid4()))
    day_index: int = Field(ge=1)
    total_days: int = Field(ge=1)
    target_exam: str = "TOEIC 600"
    sentence: str
    translation_zh: str
    subject_text: str
    verb_text: str
    object_text: str
    reading_order_steps: List[str]
    grammar_note: str
    toeic_usage_note: str
    vocabulary_items: List[MicroVocabularyItem] = Field(min_length=5, max_length=10)
    dialogue_lines: List[MicroDialogueLine]
    reading_passage: str
    comic_panels: List[ComicPanel]
    fill_blank_question: FillBlankQuestion
    completed: bool = False

    @field_validator("sentence")
    @classmethod
    def sentence_has_at_most_ten_words(cls, value: str) -> str:
        words = [word for word in value.replace(".", " ").replace("?", " ").split() if word]
        if len(words) > 10:
            raise ValueError("sentence must not exceed 10 English words")
        return value


class MicroLessonTodayResponse(BaseModel):
    success: bool = True
    diagnostic_completed: bool
    learning_plan: Optional[LearningPlan] = None
    lesson: Optional[MicroLesson] = None


class DueLearningItemCounts(BaseModel):
    vocabulary: int = 0
    grammar: int = 0
    sentence_pattern: int = 0
    legacy_vocabulary: int = 0
    total: int = 0


class WeakLearningItemCounts(BaseModel):
    vocabulary: int = 0
    grammar: int = 0
    sentence_pattern: int = 0


class SuggestedNextLesson(BaseModel):
    language: LanguageCode
    level: str
    topic: str


class CompletionSummary(BaseModel):
    current_streak: int
    longest_streak: int
    today_completed: bool
    last_active_date: Optional[str] = None
    text: str


class DailyStudyMission(BaseModel):
    diagnostic_completed: bool
    micro_lesson_status: Literal["diagnostic_required", "available", "completed", "unavailable"]
    learning_plan: Optional[LearningPlan] = None
    micro_lesson: Optional[MicroLesson] = None
    due_counts: DueLearningItemCounts
    weak_counts: WeakLearningItemCounts
    weak_items: LearningItemGroupResponse
    suggested_next_lesson: SuggestedNextLesson
    today_goal_text: str
    completion_summary: CompletionSummary


class DailyStudyMissionResponse(BaseModel):
    success: bool = True
    mission: DailyStudyMission


class MicroLessonResponse(BaseModel):
    success: bool = True
    lesson: MicroLesson


class MicroLessonAnswerRequest(BaseModel):
    answer: str


class MicroLessonAnswerResponse(BaseModel):
    success: bool = True
    correct: bool
    completed: bool
    lesson: MicroLesson
    streak: StreakInfo


# ============ Persisted Chat Models ============
ChatMessageRole: TypeAlias = Literal["system", "user", "assistant"]
ChatScenarioId: TypeAlias = Literal["daily_conversation", "travel", "restaurant", "workplace"]


def _normalize_chat_scenario_id(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in {"daily_conversation", "travel", "restaurant", "workplace"}:
        raise ValueError("scenario_id must be one of daily_conversation, travel, restaurant, workplace")
    return normalized


class ChatConversationRecord(BaseModel):
    conversation_id: str
    user_id: str
    language: LanguageCode
    scenario_id: ChatScenarioId = "daily_conversation"
    title: str
    lesson_id: Optional[str] = None
    summary: Optional[str] = None
    summary_through_sequence: int = Field(default=0, ge=0)
    summary_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    @field_validator("scenario_id", mode="before")
    @classmethod
    def normalize_scenario_id(cls, value: Any) -> str:
        return _normalize_chat_scenario_id(value)


class ChatMessageRecord(BaseModel):
    message_id: str
    conversation_id: str
    role: ChatMessageRole
    content: str
    sequence_number: int = Field(ge=1)
    metadata: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    created_at: datetime


class ChatMessagePage(BaseModel):
    messages: List[ChatMessageRecord]
    limit: int = Field(gt=0)
    has_more: bool = False
    next_before_sequence: Optional[int] = Field(default=None, ge=1)
    next_after_sequence: Optional[int] = Field(default=None, ge=1)
    descending: bool = False


def _trimmed_non_empty(value: str, *, field_name: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} must not be blank")
    return trimmed


class ChatConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: LanguageCode
    scenario_id: ChatScenarioId = "daily_conversation"
    title: str = Field(min_length=1, max_length=120)
    lesson_id: Optional[str] = None

    @field_validator("scenario_id", mode="before")
    @classmethod
    def validate_scenario_id(cls, value: Any) -> str:
        return _normalize_chat_scenario_id(value)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        trimmed = _trimmed_non_empty(value, field_name="title")
        if len(trimmed) > 120:
            raise ValueError("title must be at most 120 characters")
        return trimmed

    @field_validator("lesson_id")
    @classmethod
    def normalize_lesson_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _trimmed_non_empty(value, field_name="lesson_id")


class ChatConversationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    lesson_id: Optional[str] = None
    summary: Optional[str] = Field(default=None, max_length=12000)
    summary_through_sequence: Optional[int] = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            raise ValueError("title must not be null")
        trimmed = _trimmed_non_empty(value, field_name="title")
        if len(trimmed) > 120:
            raise ValueError("title must be at most 120 characters")
        return trimmed

    @field_validator("summary")
    @classmethod
    def validate_optional_summary(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = _trimmed_non_empty(value, field_name="summary")
        if len(trimmed) > 12000:
            raise ValueError("summary must be at most 12000 characters")
        return trimmed

    @field_validator("lesson_id")
    @classmethod
    def normalize_optional_lesson_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _trimmed_non_empty(value, field_name="lesson_id")

    @model_validator(mode="after")
    def validate_summary_checkpoint_pair(self) -> "ChatConversationUpdateRequest":
        supplied = self.model_fields_set
        if not supplied:
            raise ValueError("at least one update field is required")
        if "summary" in supplied and self.summary is not None and "summary_through_sequence" not in supplied:
            raise ValueError("summary_through_sequence is required when summary is provided")
        if "summary_through_sequence" in supplied and "summary" not in supplied:
            raise ValueError("summary must be provided when summary_through_sequence is provided")
        if "summary" in supplied and self.summary is None and self.summary_through_sequence not in (None, 0):
            raise ValueError("summary_through_sequence must be omitted or 0 when summary is null")
        return self


class ChatConversationResponse(BaseModel):
    conversation_id: str
    language: LanguageCode
    scenario_id: ChatScenarioId
    title: str
    lesson_id: Optional[str] = None
    summary: Optional[str] = None
    summary_through_sequence: int = Field(ge=0)
    summary_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    @field_validator("scenario_id", mode="before")
    @classmethod
    def normalize_scenario_id(cls, value: Any) -> str:
        return _normalize_chat_scenario_id(value)


class ChatConversationListResponse(BaseModel):
    success: bool = True
    count: int
    conversations: List[ChatConversationResponse]


class ChatConversationDetailResponse(BaseModel):
    success: bool = True
    conversation: ChatConversationResponse


class ChatConversationDeleteResponse(BaseModel):
    success: bool = True
    message: str
    conversation_id: str


class ChatScenarioResponse(BaseModel):
    scenario_id: ChatScenarioId
    language: LanguageCode
    label: str

    @field_validator("scenario_id", mode="before")
    @classmethod
    def normalize_scenario_id(cls, value: Any) -> str:
        return _normalize_chat_scenario_id(value)


class ChatScenarioListResponse(BaseModel):
    success: bool = True
    scenarios: List[ChatScenarioResponse]


class ChatMessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    role: ChatMessageRole
    content: str
    sequence_number: int = Field(ge=1)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    success: bool = True
    messages: List[ChatMessageResponse]
    limit: int = Field(ge=1, le=100)
    has_more: bool
    next_before_sequence: Optional[int] = Field(default=None, ge=1)
    next_after_sequence: Optional[int] = Field(default=None, ge=1)


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
    target_level: Optional[LearningLevel] = None

    @field_validator("target_level", mode="before")
    @classmethod
    def empty_target_level_is_unset(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_target_level_matches_language(self) -> "WritingSubmission":
        if self.target_level is not None:
            _validate_level_for_language(self.language, self.target_level)
        return self

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
    start_date: datetime = Field(default_factory=local_now)
    end_date: datetime
    milestones: List[StudyMilestone]
    daily_commitment_minutes: int
    focus_areas: List[str]
    generated_at: datetime = Field(default_factory=local_now)

# ============ API Request Models ============
class GenerateLessonRequest(BaseModel):
    """Request to generate a new lesson"""
    language: LanguageCode
    topic: Optional[str] = None
    difficulty: Optional[LearningLevel] = None  # If not provided, use current progress level
    interest_context: Optional[str] = None  # User uploaded article or interest

    @model_validator(mode="after")
    def validate_difficulty_matches_language(self) -> "GenerateLessonRequest":
        if self.difficulty is not None:
            _validate_level_for_language(self.language, self.difficulty)
        return self


class OnboardRequest(BaseModel):
    language: LanguageCode
    level: LearningLevel
    difficulty: DifficultyMode

    @model_validator(mode="after")
    def validate_level_matches_language(self) -> "OnboardRequest":
        _validate_level_for_language(self.language, self.level)
        return self


class StudyPlanGenerateRequest(BaseModel):
    target_goal: str
    language: LanguageCode


class TtsGenerateRequest(BaseModel):
    text: str
    language: LanguageCode


class SrsReviewRequest(BaseModel):
    word: str
    language: LanguageCode
    quality: int = Field(ge=0, le=5)
    client_operation_id: Optional[StrictStr] = Field(
        default=None,
        description="Optional client retry key for one legacy SRS review operation.",
    )


class LessonStartRequest(BaseModel):
    idempotency_key: Optional[StrictStr] = None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return validate_learning_session_idempotency_key(value)


class LessonQueryParams(BaseModel):
    """Query parameters for lesson listing"""
    language: Optional[LanguageCode] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    level: Optional[LearningLevel] = None
    topic: Optional[str] = None
    limit: int = 20
    offset: int = 0


class LearningSessionStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class LearningSessionEventType(str, Enum):
    lesson_started = "lesson_started"
    lesson_completed = "lesson_completed"
    review_answered = "review_answered"
    srs_reviewed = "srs_reviewed"
    chat_turn_completed = "chat_turn_completed"
    feynman_completed = "feynman_completed"
    micro_lesson_completed = "micro_lesson_completed"
    session_note = "session_note"


class LearningSessionEntityType(str, Enum):
    lesson = "lesson"
    review = "review"
    srs_item = "srs_item"
    conversation = "conversation"
    feynman_response = "feynman_response"
    micro_lesson = "micro_lesson"


def validate_learning_session_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("idempotency_key must not be blank")
    if len(normalized) > MAX_LEARNING_SESSION_IDEMPOTENCY_KEY_LENGTH:
        raise ValueError(
            f"idempotency_key must be at most {MAX_LEARNING_SESSION_IDEMPOTENCY_KEY_LENGTH} characters"
        )
    if not _IDEMPOTENCY_KEY_RE.fullmatch(normalized):
        raise ValueError("idempotency_key contains unsupported characters")
    return normalized


class LearningSessionEventMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: Optional[StrictStr] = Field(default=None, max_length=MAX_LEARNING_SESSION_NOTE_LENGTH)
    correct: Optional[bool] = None
    rating: Optional[int] = Field(default=None, ge=0, le=5)
    interval_days: Optional[int] = Field(default=None, ge=0, le=36500)
    response_time_ms: Optional[int] = Field(default=None, ge=0, le=3_600_000)
    result_category: Optional[StrictStr] = Field(default=None, max_length=64)
    lesson_category: Optional[StrictStr] = Field(default=None, max_length=64)
    completion_outcome: Optional[StrictStr] = Field(default=None, max_length=64)
    duration_seconds: Optional[int] = Field(default=None, ge=0, le=604_800)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("metadata.note must not be blank")
        return trimmed

    @field_validator("result_category", "lesson_category", "completion_outcome")
    @classmethod
    def validate_short_label(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("metadata string fields must not be blank")
        return trimmed

    @model_validator(mode="after")
    def validate_metadata(self) -> "LearningSessionEventMetadata":
        payload = self.model_dump(mode="json", exclude_none=True)
        if not payload:
            raise ValueError("metadata must include at least one supported field")
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_LEARNING_SESSION_METADATA_BYTES:
            raise ValueError(
                f"metadata must be at most {MAX_LEARNING_SESSION_METADATA_BYTES} UTF-8 bytes when serialized"
            )
        return self


class LearningSessionRecord(BaseModel):
    session_id: str
    language: LanguageCode
    status: LearningSessionStatus
    planned_minutes: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class LearningSessionEventRecord(BaseModel):
    event_id: str
    session_id: str
    event_type: LearningSessionEventType
    entity_type: Optional[LearningSessionEntityType] = None
    entity_id: Optional[str] = None
    sequence_number: int
    metadata: Optional[LearningSessionEventMetadata] = None
    occurred_at: datetime
    created_at: datetime


class LearningSessionEventTypeCounts(BaseModel):
    lesson_started: int = 0
    lesson_completed: int = 0
    review_answered: int = 0
    srs_reviewed: int = 0
    chat_turn_completed: int = 0
    feynman_completed: int = 0
    micro_lesson_completed: int = 0
    session_note: int = 0


class LearningSessionSummary(BaseModel):
    session_id: str
    language: LanguageCode
    status: LearningSessionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    planned_minutes: Optional[int] = None
    total_event_count: int
    counts_by_event_type: LearningSessionEventTypeCounts
    lesson_completion_count: int
    review_answer_count: int
    srs_review_count: int
    chat_turn_count: int
    feynman_completion_count: int
    micro_lesson_completion_count: int
    first_event_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    planned_duration_goal_reached: Optional[bool] = None
    correct_event_count: Optional[int] = None


class LearningSessionHistoryPage(BaseModel):
    sessions: List[LearningSessionRecord]
    limit: int
    has_more: bool
    next_cursor: Optional[str] = None


class LearningSessionEventHistoryPage(BaseModel):
    events: List[LearningSessionEventRecord]
    limit: int
    has_more: bool
    next_cursor: Optional[str] = None


class CreateLearningSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: LanguageCode
    planned_minutes: Optional[StrictInt] = None

    @field_validator("planned_minutes")
    @classmethod
    def validate_planned_minutes(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value <= 0 or value > MAX_LEARNING_SESSION_PLANNED_MINUTES:
            raise ValueError(
                f"planned_minutes must be between 1 and {MAX_LEARNING_SESSION_PLANNED_MINUTES}"
            )
        return value


class AppendLearningSessionEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: LearningSessionEventType
    entity_type: Optional[LearningSessionEntityType] = None
    entity_id: Optional[StrictStr] = None
    idempotency_key: Optional[StrictStr] = None
    metadata: Optional[LearningSessionEventMetadata] = None

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("entity_id must not be blank")
        if len(normalized) > MAX_LEARNING_SESSION_EVENT_ENTITY_ID_LENGTH:
            raise ValueError(
                f"entity_id must be at most {MAX_LEARNING_SESSION_EVENT_ENTITY_ID_LENGTH} characters"
            )
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return validate_learning_session_idempotency_key(value)

    @model_validator(mode="after")
    def validate_entity_shape(self) -> "AppendLearningSessionEventRequest":
        if (self.entity_type is None) != (self.entity_id is None):
            raise ValueError("entity_type and entity_id must be provided together")
        try:
            validate_event_contract(
                event_type=self.event_type.value,
                entity_type=None if self.entity_type is None else self.entity_type.value,
                entity_id=self.entity_id,
                metadata=None if self.metadata is None else self.metadata.model_dump(mode="json", exclude_none=True),
            )
        except LearningSessionContractViolation as exc:
            raise ValueError(f"learning_session_semantics: {exc}") from exc
        return self


class CompleteLearningSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: StrictStr

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return validate_learning_session_idempotency_key(value)


class AbandonLearningSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class LearningSessionDetailResponse(SuccessResponse):
    session: LearningSessionRecord


class LearningSessionActiveResponse(SuccessResponse):
    session: Optional[LearningSessionRecord] = None


class LearningSessionListResponse(SuccessResponse):
    sessions: List[LearningSessionRecord]
    limit: int
    has_more: bool
    next_cursor: Optional[str] = None


class LearningSessionEventDetailResponse(SuccessResponse):
    event: LearningSessionEventRecord


class LearningSessionEventListResponse(SuccessResponse):
    events: List[LearningSessionEventRecord]
    limit: int
    has_more: bool
    next_cursor: Optional[str] = None


class LearningSessionSummaryResponse(SuccessResponse):
    summary: LearningSessionSummary


class LearningGoalRecord(BaseModel):
    language: LanguageCode
    daily_minutes: int
    weekly_sessions: int
    weekly_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class UpdateLearningGoalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_minutes: StrictInt
    weekly_sessions: StrictInt
    weekly_minutes: Optional[StrictInt] = None

    @field_validator("daily_minutes")
    @classmethod
    def validate_daily_minutes(cls, value: int) -> int:
        if value <= 0 or value > MAX_LEARNING_GOAL_DAILY_MINUTES:
            raise ValueError(f"daily_minutes must be between 1 and {MAX_LEARNING_GOAL_DAILY_MINUTES}")
        return value

    @field_validator("weekly_sessions")
    @classmethod
    def validate_weekly_sessions(cls, value: int) -> int:
        if value <= 0 or value > MAX_LEARNING_GOAL_WEEKLY_SESSIONS:
            raise ValueError(f"weekly_sessions must be between 1 and {MAX_LEARNING_GOAL_WEEKLY_SESSIONS}")
        return value

    @field_validator("weekly_minutes")
    @classmethod
    def validate_weekly_minutes(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value <= 0 or value > MAX_LEARNING_GOAL_WEEKLY_MINUTES:
            raise ValueError(f"weekly_minutes must be between 1 and {MAX_LEARNING_GOAL_WEEKLY_MINUTES}")
        return value


class LearningGoalResponse(SuccessResponse):
    goal: LearningGoalRecord


class LearningSessionRecentSummary(BaseModel):
    session_id: str
    status: LearningSessionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    planned_minutes: Optional[int] = None
    total_event_count: int


class WeeklyLearningInsight(BaseModel):
    week_start: datetime
    week_end: datetime
    language: LanguageCode
    completed_session_count: int
    abandoned_session_count: int
    total_completed_duration_seconds: int
    active_learning_days: int
    average_completed_session_duration_seconds: Optional[int] = None
    daily_minute_goal_progress: float
    weekly_session_goal_progress: float
    weekly_minute_goal_progress: Optional[float] = None
    event_counts_by_type: LearningSessionEventTypeCounts
    lesson_completion_count: int
    review_answer_count: int
    correct_review_answer_count: int
    review_correctness_rate: Optional[float] = None
    srs_review_count: int
    chat_turn_count: int
    feynman_completion_count: int
    micro_lesson_completion_count: int
    most_active_day: Optional[str] = None
    recent_completed_sessions: List[LearningSessionRecentSummary] = Field(default_factory=list)
    goal: LearningGoalRecord


class WeeklyLearningInsightResponse(SuccessResponse):
    insight: WeeklyLearningInsight


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
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    memory_tip: Optional[str] = None
    root: Optional[str] = None
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
    part_of_speech: Optional[str] = None
    root: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    word_family: Optional[List[str]] = None
    memory_tip: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source_lesson_id: Optional[str] = None
    mastery_state: str = "new"
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
    timestamp: datetime


class ReadyCheckResponse(BaseModel):
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
    latest_accuracy_rate: float
    best_accuracy_rate: float
    submitted_at: datetime


class AnalyticsWeakLearningItem(BaseModel):
    item_key: str
    mastery_state: LearningMasteryState
    review_count: int = 0
    incorrect_count: int = 0
    average_rating: float = 0.0


class AnalyticsReviewCountPoint(BaseModel):
    date: str
    count: int


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
    mastery_state_counts: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    weakest_vocabulary: List[AnalyticsWeakLearningItem] = Field(default_factory=list)
    weakest_grammar: List[AnalyticsWeakLearningItem] = Field(default_factory=list)
    weakest_sentence_patterns: List[AnalyticsWeakLearningItem] = Field(default_factory=list)
    recent_7_day_review_counts: List[AnalyticsReviewCountPoint] = Field(default_factory=list)


class AnalyticsResponse(SuccessResponse):
    analytics: AnalyticsPayload
