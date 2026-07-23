export type Language = 'EN' | 'JP'
export type EnglishLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1'
export type JapaneseLevel = 'N5' | 'N4' | 'N3' | 'N2' | 'N1'
export type LearningLevel = EnglishLevel | JapaneseLevel
export type DifficultyMode = 'easy' | 'normal' | 'hardcore'

export type ErrorType = 'spelling' | 'grammar' | 'vocabulary' | 'comprehension'

export interface ApiErrorPayload {
  error: boolean
  message: string
  code: string
  detail?: unknown
}

export interface VocabularyItem {
  word: string
  reading?: string | null
  phonetic?: string | null
  definition_zh: string
  example_sentence: string
  example_translation: string
  part_of_speech?: string | null
  root?: string | null
  prefix?: string | null
  suffix?: string | null
  word_family?: string[] | null
  memory_tip?: string | null
  category?: string | null
  tags?: string[] | null
}

export interface GrammarExample {
  sentence: string
  translation: string
}

export interface GrammarExercise {
  question: string
  options?: string[]
  correct_answer: string
  explanation: string
  related_vocabulary?: string[]
  related_grammar?: string[]
  related_sentence_patterns?: string[]
}

export interface GrammarSection {
  title: string
  explanation: string
  examples: GrammarExample[]
  exercises: GrammarExercise[]
}

export interface ReadingQuestion {
  question: string
  options: string[]
  correct_answer: string
  explanation: string
  related_vocabulary?: string[]
  related_grammar?: string[]
  related_sentence_patterns?: string[]
}

export interface ReadingSection {
  title: string
  content: string
  word_count: number
  questions: ReadingQuestion[]
}

export interface DialogueLine {
  speaker: string
  text: string
  translation: string
}

export interface DialogueAlternative {
  original: string
  alternative: string
  context: string
}

export interface DialogueSection {
  scenario: string
  context: string
  dialogue: DialogueLine[]
  alternatives: DialogueAlternative[]
}

export interface SentencePattern {
  pattern: string
  meaning_zh: string
  usage_note: string
  examples: GrammarExample[]
}

export interface WordRoot {
  root: string
  meaning_zh: string
  examples: string[]
  memory_tip: string
}

export interface ImmersionSection {
  shadowing_text: DialogueLine[]
  repeat_chunks: string[]
  listening_tips: string[]
}

export interface FeynmanPrompt {
  prompt: string
  checklist: string[]
}

export interface FeynmanFeedback {
  summary: string
  strengths: string[]
  missing_points: string[]
  corrections: string[]
  suggested_simple_explanation: string
  related_weak_items: string[]
  score: number
}

export interface ReviewPlan {
  today: string[]
  next_1_day: string[]
  next_3_days: string[]
  next_7_days: string[]
}

export interface LessonMetadata {
  lesson_id: string
  language: Language
  level: string
  topic: string
  generated_at: string
  estimated_duration_minutes: number
  key_points: string[]
}

export interface WordCard {
  word: string
  rarity: 'C' | 'B' | 'A' | 'S' | 'SS'
  collected_at: string
  language: Language
  reading?: string | null
  phonetic?: string | null
  definition_zh?: string
  example_sentence?: string
  example_translation?: string
}

export interface Lesson {
  metadata: LessonMetadata
  objectives?: string[]
  vocabulary: VocabularyItem[]
  word_roots?: WordRoot[]
  sentence_patterns?: SentencePattern[]
  grammar: GrammarSection
  reading: ReadingSection
  dialogue: DialogueSection
  immersion?: ImmersionSection
  feynman_prompt?: FeynmanPrompt
  review_plan?: ReviewPlan
  evidence?: LessonEvidence[]
  gamification?: {
    xp_added: number
    leveled_up: boolean
    new_cards: WordCard[]
  }
}

export interface LessonEvidence {
  material_id: string
  doc_id?: string | null
  text: string
  source: string
  title: string
  language?: string | null
  source_type?: string | null
  uploaded_at?: string | null
  total_chunks: number
  chunk_index: number
}

export interface LessonListItem {
  lesson_id: string
  user_id: string
  language: Language
  level: string
  topic: string
  generated_at: string
  estimated_duration_minutes?: number | null
  key_points?: string[] | string | null
  file_path: string
  created_at?: string | null
}

export interface LanguageProgress {
  language: Language
  current_level: string
  target_level: string
  completed_lessons: number
  total_exercises: number
  correct_exercises: number
  accuracy_rate: number
  last_study_date: string | null
}

export interface Achievement {
  id: string
  title: string
  description: string
  icon: string
  unlocked_at: string
  rarity: 'common' | 'rare' | 'epic' | 'legendary'
}

export interface UserRPGStats {
  level: number
  current_xp: number
  next_level_xp: number
  total_xp: number
  avatar_url: string
  title: string
  unlocked_skills: string[]
  achievements: Achievement[]
  word_cards: WordCard[]
  streak_days: number
  difficulty_mode: string
  is_onboarded: boolean
  error_distribution: Record<ErrorType, number> | Record<string, number>
}

export interface UserProgress {
  user_id: string
  english_progress: LanguageProgress
  japanese_progress: LanguageProgress
  rpg_stats: UserRPGStats
  updated_at: string
}

export interface ProgressResponse {
  success: boolean
  progress: UserProgress
  streak: StreakInfo
}

export interface ReviewAnswer {
  lesson_id: string
  exercise_type: 'grammar' | 'reading'
  question_index: number
  user_answer: string
  correct_answer: string
  client_submission_id?: string
}

export interface ReviewResult {
  success: boolean
  total_questions: number
  correct_count: number
  accuracy_rate: number
  incorrect_items: Array<{
    question: string
    user_answer: string
    correct_answer: string
    explanation: string
  }>
  gamification: {
    xp_added: number
    leveled_up: boolean
  }
}

export type LearningItemType = 'vocabulary' | 'grammar' | 'sentence_pattern'
export type LearningMasteryState =
  | 'new'
  | 'learning'
  | 'review'
  | 'weak'
  | 'mastered'

export interface LearningItemDue {
  item_id: string
  item_type: LearningItemType
  item_key: string
  language: Language
  level?: string | null
  content: Record<string, unknown>
  category?: string | null
  tags: string[]
  root?: string | null
  memory_tip?: string | null
  mastery_state: LearningMasteryState
  due_at: string
}

export interface LearningItemDueResponse {
  success: boolean
  items: LearningItemDue[]
}

export interface LearningItemWeakResponse {
  success: boolean
  vocabulary: LearningItemDue[]
  grammar: LearningItemDue[]
  sentence_pattern: LearningItemDue[]
}

export interface DueLearningItemCounts {
  vocabulary: number
  grammar: number
  sentence_pattern: number
  legacy_vocabulary: number
  total: number
}

export interface WeakLearningItemCounts {
  vocabulary: number
  grammar: number
  sentence_pattern: number
}

export interface SuggestedNextLesson {
  language: Language
  level: string
  topic: string
}

export interface CompletionSummary {
  current_streak: number
  longest_streak: number
  today_completed: boolean
  last_active_date: string | null
  text: string
}

export interface DailyStudyMission {
  diagnostic_completed: boolean
  micro_lesson_status:
    | 'diagnostic_required'
    | 'available'
    | 'completed'
    | 'unavailable'
  learning_plan: LearningPlan | null
  micro_lesson: MicroLesson | null
  due_counts: DueLearningItemCounts
  weak_counts: WeakLearningItemCounts
  weak_items: LearningItemWeakResponse
  suggested_next_lesson: SuggestedNextLesson
  today_goal_text: string
  completion_summary: CompletionSummary
}

export interface DailyStudyMissionResponse {
  success: boolean
  mission: DailyStudyMission
}

export interface LearningItemReviewResult {
  success: boolean
  item_id: string
  interval_days: number
  ease_factor: number
  repetitions: number
  lapses: number
  due_at: string
  last_reviewed_at?: string | null
  mastery_state: LearningMasteryState
}

export interface FeynmanFeedbackResponse {
  success: boolean
  feedback: FeynmanFeedback
}

export interface WritingSubmission {
  language: Language
  text: string
  topic?: string
  target_level?: LearningLevel | ''
}

export interface TtsRequest {
  text: string
  language: Language
}

export interface OnboardRequest {
  language: Language
  level: LearningLevel
  difficulty: DifficultyMode
}

export interface StudyPlanGenerateRequest {
  target_goal: string
  language: Language
}

export interface WritingAnalysis {
  original_text: string
  corrected_text: string
  grammar_score: number
  vocabulary_score: number
  style_score: number
  overall_score: number
  estimated_level: string
  corrections: Array<{
    original: string
    corrected: string
    explanation: string
    type: string
  }>
  suggestions: string[]
  feedback: string
}

export interface StudyMilestone {
  title: string
  description: string
  target_date: string
  required_skills: string[]
  is_completed: boolean
}

export interface StudyPlan {
  plan_id: string
  user_id: string
  target_goal: string
  language: Language
  start_date: string
  end_date: string
  milestones: StudyMilestone[]
  daily_commitment_minutes: number
  focus_areas: string[]
  generated_at: string
}

export interface GenerateLessonRequest {
  language: Language
  topic?: string
  difficulty?: LearningLevel
  interest_context?: string
}

export interface GenerationTask {
  task_id: string
  user_id: string
  status:
    | 'pending'
    | 'running'
    | 'success'
    | 'fallback_success'
    | 'failed'
    | 'retried'
  model_used: string
  duration_ms: number
  error_message?: string
  retry_count: number
  created_at: string
}

export type WrongAnswerStatus = 'active' | 'mastered'

export interface WrongAnswer {
  id: number
  user_id: string
  language: Language
  question_type: string
  question: string
  user_answer: string
  correct_answer: string
  source_lesson_id?: string | null
  status: WrongAnswerStatus
  wrong_count: number
  created_at: string
  updated_at: string
}

export interface WrongAnswerListResponse {
  success: boolean
  count: number
  items: WrongAnswer[]
}

export interface WrongAnswerItemResponse {
  success: boolean
  item: WrongAnswer
}

export interface WrongAnswerRetryResponse {
  success: boolean
  correct: boolean
  item: WrongAnswer
}

export interface StreakInfo {
  current_streak: number
  longest_streak: number
  last_active_date: string | null
  today_completed: boolean
}

export interface StreakResponse extends StreakInfo {
  success: boolean
}

export interface AnalyticsHardestWord {
  word: string
  mistakes: number
}

export interface AnalyticsWeakestCategory {
  category: string
  active_items: number
}

export interface AnalyticsTrendPoint {
  lesson_id: string | null
  latest_accuracy_rate: number
  best_accuracy_rate: number
  submitted_at: string
}

export interface AnalyticsPayload {
  total_xp: number
  level: number
  streak: number
  longest_streak: number
  lessons_completed: number
  hardest_words: AnalyticsHardestWord[]
  weakest_category: AnalyticsWeakestCategory | null
  accuracy_trend: AnalyticsTrendPoint[]
  today_completed: boolean
  mastery_state_counts?: Record<
    LearningItemType,
    Partial<Record<LearningMasteryState, number>>
  >
  weakest_vocabulary?: AnalyticsWeakLearningItem[]
  weakest_grammar?: AnalyticsWeakLearningItem[]
  weakest_sentence_patterns?: AnalyticsWeakLearningItem[]
  recent_7_day_review_counts?: AnalyticsReviewCountPoint[]
}

export interface AnalyticsWeakLearningItem {
  item_key: string
  mastery_state: LearningMasteryState
  review_count: number
  incorrect_count: number
  average_rating: number
}

export interface AnalyticsReviewCountPoint {
  date: string
  count: number
}

export interface AnalyticsResponse {
  success: boolean
  analytics: AnalyticsPayload
}

export interface TtsResponse {
  success: boolean
  available: boolean
  audio_url: string | null
  mode: 'live' | 'preview'
  message?: string | null
}

export interface RagMaterial {
  material_id: string
  doc_id: string
  source: string
  title: string
  language: Language
  source_type?: string | null
  uploaded_at?: string | null
  total_chunks: number
  text?: string | null
}

export interface RagMaterialsResponse {
  success: boolean
  items: RagMaterial[]
}

export interface ImportedVocabularyItem {
  id: number
  user_id: string
  language: Language
  word: string
  reading: string | null
  definition_zh: string
  example_sentence: string | null
  example_translation: string | null
  part_of_speech?: string | null
  root?: string | null
  prefix?: string | null
  suffix?: string | null
  word_family?: string[] | null
  memory_tip?: string | null
  category?: string | null
  tags?: string[] | null
  source_lesson_id?: string | null
  mastery_state?: string
  created_at: string
}

export interface ImportedVocabularyListResponse {
  success: boolean
  count: number
  items: ImportedVocabularyItem[]
}

export interface SrsItem {
  word: string
  language: Language
  definition_zh?: string | null
  category?: string | null
  tags?: string[] | null
  memory_tip?: string | null
  root?: string | null
  next_review: string | null
  interval: number
  ease_factor: number
  srs_level: number
}

export interface SrsDueResponse {
  success: boolean
  items: SrsItem[]
}

export interface SrsReviewRequest {
  word: string
  language: Language
  quality: number
  client_operation_id?: string
}

export interface DemoResetResponse {
  success: boolean
  message: string
  summary: {
    lessons: number
    imported_vocabulary: number
    wrong_answers: number
    today_lesson_id: string
  }
}

export type ChatScenarioId =
  | 'daily_conversation'
  | 'travel'
  | 'restaurant'
  | 'workplace'

export interface ChatScenario {
  scenario_id: ChatScenarioId
  language: Language
  label: string
}

export interface ChatScenarioListResponse {
  success: boolean
  scenarios: ChatScenario[]
}

export interface ChatConversation {
  conversation_id: string
  language: Language
  scenario_id: ChatScenarioId
  title: string
  lesson_id?: string | null
  summary?: string | null
  summary_through_sequence: number
  summary_updated_at?: string | null
  created_at: string
  updated_at: string
  last_message_at?: string | null
}

export interface ChatConversationListResponse {
  success: boolean
  count: number
  conversations: ChatConversation[]
}

export interface ChatConversationDetailResponse {
  success: boolean
  conversation: ChatConversation
}

export interface ChatConversationDeleteResponse {
  success: boolean
  message: string
  conversation_id: string
}

export interface ChatMessage {
  message_id: string
  conversation_id: string
  role: 'system' | 'user' | 'assistant'
  content: string
  sequence_number: number
  metadata?: Record<string, unknown> | null
  created_at: string
}

export interface ChatMessageListResponse {
  success: boolean
  messages: ChatMessage[]
  limit: number
  has_more: boolean
  next_before_sequence?: number | null
  next_after_sequence?: number | null
}

export interface DiagnosticQuestion {
  question_id: string
  prompt: string
  choices: string[]
  skill: 'subject' | 'verb' | 'present_simple'
}

export interface LearningPlan {
  estimated_total_days: number
  current_day: number
  summary_zh: string
}

export interface MicroVocabularyItem {
  word: string
  phonetic: string
  pronunciation_zh: string
  definition_zh: string
  example_sentence: string
  example_translation: string
}

export interface MicroDialogueLine {
  speaker: string
  english: string
  translation_zh: string
}

export interface ComicPanel {
  panel: number
  english: string
  translation_zh: string
  scene_prompt: string
}

export interface FillBlankQuestion {
  prompt: string
  choices: string[]
  correct_answer: string
  explanation: string
}

export interface MicroLesson {
  lesson_id: string
  day_index: number
  total_days: number
  target_exam: string
  sentence: string
  translation_zh: string
  subject_text: string
  verb_text: string
  object_text: string
  reading_order_steps: string[]
  grammar_note: string
  toeic_usage_note: string
  vocabulary_items: MicroVocabularyItem[]
  dialogue_lines: MicroDialogueLine[]
  reading_passage: string
  comic_panels: ComicPanel[]
  fill_blank_question: FillBlankQuestion
  completed: boolean
}

export interface MicroLessonTodayResponse {
  success: boolean
  diagnostic_completed: boolean
  learning_plan: LearningPlan | null
  lesson: MicroLesson | null
}

export interface MicroLessonAnswerResponse {
  success: boolean
  correct: boolean
  completed: boolean
  lesson: MicroLesson
  streak: StreakInfo
}

export type LearningSessionStatus = 'active' | 'completed' | 'abandoned'
export type LearningSessionEventType =
  | 'lesson_started'
  | 'lesson_completed'
  | 'review_answered'
  | 'srs_reviewed'
  | 'chat_turn_completed'
  | 'feynman_completed'
  | 'micro_lesson_completed'
  | 'session_note'
export type LearningSessionEntityType =
  | 'lesson'
  | 'review'
  | 'srs_item'
  | 'conversation'
  | 'feynman_response'
  | 'micro_lesson'

export interface LearningSessionRecord {
  session_id: string
  language: Language
  status: LearningSessionStatus
  planned_minutes?: number | null
  started_at: string
  ended_at?: string | null
  duration_seconds?: number | null
  created_at: string
  updated_at: string
}

export interface LearningSessionEventMetadata {
  note?: string
  correct?: boolean
  rating?: number
  interval_days?: number
  response_time_ms?: number
  result_category?: string
  lesson_category?: string
  completion_outcome?: string
  duration_seconds?: number
}

export interface LearningSessionEventRecord {
  event_id: string
  session_id: string
  event_type: LearningSessionEventType
  entity_type?: LearningSessionEntityType | null
  entity_id?: string | null
  sequence_number: number
  metadata?: LearningSessionEventMetadata | null
  occurred_at: string
  created_at: string
}

export interface LearningSessionEventCounts {
  lesson_started: number
  lesson_completed: number
  review_answered: number
  srs_reviewed: number
  chat_turn_completed: number
  feynman_completed: number
  micro_lesson_completed: number
  session_note: number
}

export interface LearningSessionSummary {
  session_id: string
  language: Language
  status: LearningSessionStatus
  started_at: string
  ended_at?: string | null
  duration_seconds?: number | null
  planned_minutes?: number | null
  total_event_count: number
  counts_by_event_type: LearningSessionEventCounts
  lesson_completion_count: number
  review_answer_count: number
  srs_review_count: number
  chat_turn_count: number
  feynman_completion_count: number
  micro_lesson_completion_count: number
  first_event_at?: string | null
  last_event_at?: string | null
  planned_duration_goal_reached?: boolean | null
  correct_event_count?: number | null
}

export interface LearningGoal {
  language: Language
  daily_minutes: number
  weekly_sessions: number
  weekly_minutes?: number | null
  created_at: string
  updated_at: string
}

export interface WeeklyLearningInsight {
  week_start: string
  week_end: string
  language: Language
  completed_session_count: number
  abandoned_session_count: number
  total_completed_duration_seconds: number
  active_learning_days: number
  average_completed_session_duration_seconds?: number | null
  daily_minute_goal_progress: number
  weekly_session_goal_progress: number
  weekly_minute_goal_progress?: number | null
  event_counts_by_type: LearningSessionEventCounts
  lesson_completion_count: number
  review_answer_count: number
  correct_review_answer_count: number
  review_correctness_rate?: number | null
  srs_review_count: number
  chat_turn_count: number
  feynman_completion_count: number
  micro_lesson_completion_count: number
  most_active_day?: string | null
  recent_completed_sessions: Array<{
    session_id: string
    status: LearningSessionStatus
    started_at: string
    ended_at?: string | null
    duration_seconds?: number | null
    planned_minutes?: number | null
    total_event_count: number
  }>
  goal: LearningGoal
}
