export type Language = 'EN' | 'JP'

export interface VocabularyItem {
  word: string
  reading?: string | null
  phonetic?: string | null
  definition_zh: string
  example_sentence: string
  example_translation: string
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
  vocabulary: VocabularyItem[]
  grammar: GrammarSection
  reading: ReadingSection
  dialogue: DialogueSection
  evidence?: Array<{
    text: string
    source: string
    chunk_index: number
  }>
  gamification?: {
    xp_added: number
    leveled_up: boolean
    new_cards: WordCard[]
  }
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
  error_distribution: Record<string, number>
}

export interface UserProgress {
  user_id: string
  english_progress: LanguageProgress
  japanese_progress: LanguageProgress
  rpg_stats: UserRPGStats
  updated_at: string
}

export interface ReviewAnswer {
  lesson_id: string
  exercise_type: 'grammar' | 'reading'
  question_index: number
  user_answer: string
  correct_answer: string
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

export interface WritingSubmission {
  language: Language
  text: string
  topic?: string
  target_level?: string
}

export interface WritingAnalysis {
  original_text: string
  corrected_text: string
  grammar_score: number
  vocabulary_score: number
  style_score: number
  overall_score: number
  estimated_level: string
  corrections: Array<{ original: string; corrected: string; explanation: string; type: string }>
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
  difficulty?: string
  interest_context?: string
}

export interface GenerationTask {
  task_id: string
  user_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'retried'
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

export interface StreakResponse {
  success: boolean
  current_streak: number
  longest_streak: number
  last_active_date: string | null
  today_completed: boolean
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
  lesson_id: string
  accuracy_rate: number
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
}

export interface AnalyticsResponse {
  success: boolean
  analytics: AnalyticsPayload
}
