export interface VocabularyItem {
  word: string
  reading?: string
  phonetic?: string
  definition_zh: string
  example_sentence: string
  example_translation: string
  synonyms?: string[]
  antonyms?: string[]
}

export interface GrammarExample {
  sentence: string
  translation: string
}

export interface GrammarExercise {
  question: string
  options: string[]
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
  language: 'EN' | 'JP'
  level: string
  topic: string
  generated_at: string
  estimated_duration_minutes: number
  key_points: string[]
}

export interface Lesson {
  metadata: LessonMetadata
  vocabulary: VocabularyItem[]
  grammar: GrammarSection
  reading: ReadingSection
  dialogue: DialogueSection
}

export interface LanguageProgress {
  language: 'EN' | 'JP'
  current_level: string
  target_level: string
  completed_lessons: number
  total_exercises: number
  correct_exercises: number
  accuracy_rate: number
  last_study_date: string | null
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

export interface Achievement {
  id: string
  title: string
  description: string
  icon: string
  unlocked_at: string
  rarity: 'common' | 'rare' | 'epic' | 'legendary'
}

export interface WordCard {
  word: string
  rarity: 'C' | 'B' | 'A' | 'S' | 'SS'
  collected_at: string
}

export interface ReviewAnswer {
  lesson_id: string
  exercise_type: 'grammar' | 'reading'
  question_index: number
  user_answer: string
  correct_answer: string
}

export interface ReviewResultData {
  total_questions: number
  correct_count: number
  accuracy_rate: number
  incorrect_items: Array<{
    question: string
    user_answer: string
    correct_answer: string
    explanation: string
  }>
}

export interface ReviewApiResponse {
  success: boolean
  gamification: {
    xp_added: number
    leveled_up: boolean
  }
  data: ReviewResultData
}

export interface GenerateLessonRequest {
  language: 'EN' | 'JP'
  topic?: string
  difficulty?: string
}