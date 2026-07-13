import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Analytics from '@/views/Analytics.vue'
import Materials from '@/views/Materials.vue'
import LearningWorkspace from '@/views/LearningWorkspace.vue'
import Progress from '@/views/Progress.vue'
import TodayLesson from '@/views/TodayLesson.vue'
import Vocabulary from '@/views/Vocabulary.vue'
import WrongAnswers from '@/views/WrongAnswers.vue'
import type {
  AnalyticsResponse,
  DailyStudyMissionResponse,
  Language,
  Lesson,
  MicroLesson,
  ProgressResponse,
  RagMaterialsResponse,
  ReviewResult,
  StreakResponse,
  UserProgress,
  WrongAnswerListResponse,
  WrongAnswerRetryResponse,
} from '@/types'

const routeState = vi.hoisted(() => ({
  query: {} as Record<string, string>,
}))

const apiMocks = vi.hoisted(() => ({
  getProgress: vi.fn(),
  getAnalytics: vi.fn(),
  listRagMaterials: vi.fn(),
  uploadRagMaterial: vi.fn(),
  deleteRagMaterial: vi.fn(),
  listImportedVocabulary: vi.fn(),
  deleteImportedVocabulary: vi.fn(),
  listWrongAnswers: vi.fn(),
  updateStatus: vi.fn(),
  deleteWrongAnswer: vi.fn(),
  retryWrongAnswer: vi.fn(),
  getTodayLesson: vi.fn(),
  generateLesson: vi.fn(),
  getTts: vi.fn(),
  submitReview: vi.fn(),
  getStreak: vi.fn(),
  resetDemo: vi.fn(),
  exportPdf: vi.fn(),
  getDiagnosticQuestions: vi.fn(),
  submitDiagnostic: vi.fn(),
  getMicroToday: vi.fn(),
  answerMicroLesson: vi.fn(),
  getTodayMission: vi.fn(),
}))

const feedbackMocks = vi.hoisted(() => ({
  showNotice: vi.fn(),
  requestConfirmation: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, string | number>) => {
      if (!params) return key
      return `${key} ${Object.values(params).join(' ')}`
    },
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
}))

vi.mock('@/services/api', () => ({
  progressApi: {
    getProgress: apiMocks.getProgress,
  },
  analyticsApi: {
    getAnalytics: apiMocks.getAnalytics,
  },
  importApi: {
    listRagMaterials: apiMocks.listRagMaterials,
    uploadRagMaterial: apiMocks.uploadRagMaterial,
    deleteRagMaterial: apiMocks.deleteRagMaterial,
    listImportedVocabulary: apiMocks.listImportedVocabulary,
    deleteImportedVocabulary: apiMocks.deleteImportedVocabulary,
  },
  wrongAnswerApi: {
    listWrongAnswers: apiMocks.listWrongAnswers,
    updateStatus: apiMocks.updateStatus,
    deleteWrongAnswer: apiMocks.deleteWrongAnswer,
    retry: apiMocks.retryWrongAnswer,
  },
  lessonApi: {
    getTodayLesson: apiMocks.getTodayLesson,
    generateLesson: apiMocks.generateLesson,
    exportPdf: apiMocks.exportPdf,
    getTts: apiMocks.getTts,
  },
  reviewApi: {
    submitReview: apiMocks.submitReview,
  },
  streakApi: {
    getStreak: apiMocks.getStreak,
  },
  systemApi: {
    resetDemo: apiMocks.resetDemo,
  },
  diagnosticApi: {
    getQuestions: apiMocks.getDiagnosticQuestions,
    submit: apiMocks.submitDiagnostic,
  },
  microLessonApi: {
    getToday: apiMocks.getMicroToday,
    answer: apiMocks.answerMicroLesson,
  },
  studyApi: {
    getTodayMission: apiMocks.getTodayMission,
  },
}))

vi.mock('@/services/appFeedback', () => ({
  showNotice: feedbackMocks.showNotice,
  requestConfirmation: feedbackMocks.requestConfirmation,
}))

const flushPromises = () =>
  new Promise((resolve) => window.setTimeout(resolve, 0))

const streak = (overrides: Partial<StreakResponse> = {}): StreakResponse => ({
  success: true,
  current_streak: 3,
  longest_streak: 5,
  last_active_date: '2026-05-11',
  today_completed: true,
  ...overrides,
})

const languageProgress = (language: Language, completedLessons: number) => ({
  language,
  current_level: language === 'EN' ? 'A2' : 'N5',
  target_level: language === 'EN' ? 'B1' : 'N4',
  completed_lessons: completedLessons,
  total_exercises: 10,
  correct_exercises: 8,
  accuracy_rate: 80,
  last_study_date: '2026-05-11T00:00:00',
})

const progressPayload = (): ProgressResponse => ({
  success: true,
  progress: {
    user_id: 'default_user',
    english_progress: languageProgress('EN', 4),
    japanese_progress: languageProgress('JP', 2),
    rpg_stats: {
      level: 2,
      current_xp: 40,
      next_level_xp: 100,
      total_xp: 140,
      avatar_url: '',
      title: 'Careful Learner',
      unlocked_skills: ['review'],
      achievements: [],
      word_cards: [
        {
          word: 'hello',
          rarity: 'C',
          collected_at: '2026-05-10T00:00:00',
          language: 'EN',
          definition_zh: 'greeting',
        },
      ],
      streak_days: 3,
      difficulty_mode: 'normal',
      is_onboarded: true,
      error_distribution: {},
    },
    updated_at: '2026-05-11T12:00:00',
  } satisfies UserProgress,
  streak: streak(),
})

const analyticsPayload = (
  overrides: Partial<AnalyticsResponse['analytics']> = {},
): AnalyticsResponse => ({
  success: true,
  analytics: {
    total_xp: 140,
    level: 2,
    streak: 3,
    longest_streak: 5,
    lessons_completed: 6,
    hardest_words: [{ word: 'difficult phrase', mistakes: 2 }],
    weakest_category: { category: 'grammar', active_items: 1 },
    accuracy_trend: [
      {
        lesson_id: null,
        latest_accuracy_rate: 75,
        best_accuracy_rate: 90,
        submitted_at: '2026-05-10T00:00:00',
      },
      {
        lesson_id: 'lesson-2',
        latest_accuracy_rate: 100,
        best_accuracy_rate: 100,
        submitted_at: '2026-05-11T00:00:00',
      },
    ],
    today_completed: true,
    mastery_state_counts: {
      vocabulary: { weak: 1 },
      grammar: { learning: 1 },
      sentence_pattern: { review: 1 },
    },
    weakest_vocabulary: [
      {
        item_key: 'invoice',
        mastery_state: 'weak',
        review_count: 2,
        incorrect_count: 2,
        average_rating: 1,
      },
    ],
    weakest_grammar: [
      {
        item_key: 'Present Simple',
        mastery_state: 'learning',
        review_count: 1,
        incorrect_count: 0,
        average_rating: 4,
      },
    ],
    weakest_sentence_patterns: [],
    recent_7_day_review_counts: [{ date: '2026-05-11', count: 3 }],
    ...overrides,
  },
})

const materialsPayload = (
  items: RagMaterialsResponse['items'],
): RagMaterialsResponse => ({
  success: true,
  items,
})

const wrongAnswersPayload = (
  items: WrongAnswerListResponse['items'],
): WrongAnswerListResponse => ({
  success: true,
  count: items.length,
  items,
})

const lessonPayload = (): Lesson => ({
  metadata: {
    lesson_id: 'lesson-1',
    language: 'EN',
    level: 'A1',
    topic: 'Travel',
    generated_at: '2026-05-11T00:00:00',
    estimated_duration_minutes: 10,
    key_points: ['greetings'],
  },
  objectives: [
    'Use travel greetings.',
    'Practice a sentence pattern.',
    'Explain the dialogue.',
  ],
  vocabulary: [
    {
      word: 'hello',
      phonetic: 'heh-loh',
      definition_zh: 'greeting',
      example_sentence: 'Hello there.',
      example_translation: 'A greeting.',
      root: 'hel',
      memory_tip: 'Connect it to greeting someone.',
      category: 'greetings',
      tags: ['speaking'],
    },
  ],
  word_roots: [
    {
      root: 're-',
      meaning_zh: 'again',
      examples: ['review', 'repeat'],
      memory_tip: 'Do it again.',
    },
  ],
  sentence_patterns: [
    {
      pattern: 'I would like ...',
      meaning_zh: '我想要……',
      usage_note: 'Use it for polite requests.',
      examples: [{ sentence: 'I would like tea.', translation: '我想要茶。' }],
    },
  ],
  grammar: {
    title: 'Be verbs',
    explanation: 'Use am/is/are.',
    examples: [],
    exercises: [
      {
        question: 'I ___ a student.',
        options: ['am', 'is', 'are'],
        correct_answer: 'am',
        explanation: 'Use am with I.',
      },
    ],
  },
  reading: {
    title: 'Cafe',
    content: 'A short reading.',
    word_count: 3,
    questions: [
      {
        question: 'Where is it?',
        options: ['Cafe', 'Station', 'Library'],
        correct_answer: 'Cafe',
        explanation: 'The passage says cafe.',
      },
    ],
  },
  dialogue: {
    scenario: 'Cafe',
    context: 'Ordering',
    dialogue: [
      { speaker: 'A', text: 'Hello.', translation: '你好。' },
      { speaker: 'B', text: 'I would like tea.', translation: '我想要茶。' },
    ],
    alternatives: [],
  },
  immersion: {
    shadowing_text: [
      { speaker: 'Coach', text: 'Hello there.', translation: '你好。' },
    ],
    repeat_chunks: ['Hello there'],
    listening_tips: ['Listen for stress.'],
  },
  feynman_prompt: {
    prompt: 'Explain the cafe greeting.',
    checklist: ['Use hello.', 'Use one pattern.'],
  },
  review_plan: {
    today: ['Read aloud.'],
    next_1_day: ['Review hello.'],
    next_3_days: ['Write a request.'],
    next_7_days: ['Retake questions.'],
  },
})

const microLessonPayload = (
  overrides: Partial<MicroLesson> = {},
): MicroLesson => ({
  lesson_id: 'micro-1',
  day_index: 1,
  total_days: 90,
  target_exam: 'TOEIC 600',
  sentence: 'We raise prices today.',
  translation_zh: '我們今天調高價格。',
  subject_text: 'We',
  verb_text: 'raise',
  object_text: 'prices',
  reading_order_steps: ['Find We.', 'Find raise.', 'Find prices.'],
  grammar_note: 'Use present simple with We.',
  toeic_usage_note: 'TOEIC uses raise prices often.',
  vocabulary_items: [
    {
      word: 'raise',
      phonetic: '/reɪz/',
      pronunciation_zh: '雷茲',
      definition_zh: '提高',
      example_sentence: 'We raise prices today.',
      example_translation: '我們今天調高價格。',
    },
    {
      word: 'price',
      phonetic: '/praɪs/',
      pronunciation_zh: '普賴斯',
      definition_zh: '價格',
      example_sentence: 'The price is high.',
      example_translation: '價格很高。',
    },
    {
      word: 'today',
      phonetic: '/təˈdeɪ/',
      pronunciation_zh: '特-day',
      definition_zh: '今天',
      example_sentence: 'We meet today.',
      example_translation: '我們今天見面。',
    },
    {
      word: 'customer',
      phonetic: '/ˈkʌstəmər/',
      pronunciation_zh: '卡斯特默',
      definition_zh: '顧客',
      example_sentence: 'Customers need help.',
      example_translation: '顧客需要協助。',
    },
    {
      word: 'report',
      phonetic: '/rɪˈpɔːrt/',
      pronunciation_zh: '瑞波特',
      definition_zh: '報告',
      example_sentence: 'I read the report.',
      example_translation: '我閱讀報告。',
    },
  ],
  dialogue_lines: [
    {
      speaker: 'A',
      english: 'Do we raise prices today?',
      translation_zh: '我們今天調高價格嗎？',
    },
  ],
  reading_passage: 'A team checks the report.',
  comic_panels: [
    {
      panel: 1,
      english: 'We check the report.',
      translation_zh: '我們查看報告。',
      scene_prompt: 'Office report.',
    },
  ],
  fill_blank_question: {
    prompt: 'We ___ prices today.',
    choices: ['raise', 'raises', 'raising'],
    correct_answer: 'raise',
    explanation: 'We uses raise.',
  },
  completed: false,
  ...overrides,
})

const microTodayPayload = (
  lesson: MicroLesson | null = microLessonPayload(),
) => ({
  success: true,
  diagnostic_completed: true,
  learning_plan: {
    estimated_total_days: 90,
    current_day: 1,
    summary_zh: '每日練習短句。',
  },
  lesson,
})

const todayMissionPayload = (): DailyStudyMissionResponse => ({
  success: true,
  mission: {
    diagnostic_completed: true,
    micro_lesson_status: 'available',
    learning_plan: {
      estimated_total_days: 90,
      current_day: 1,
      summary_zh: 'ready',
    },
    micro_lesson: microLessonPayload(),
    due_counts: {
      vocabulary: 2,
      grammar: 1,
      sentence_pattern: 1,
      legacy_vocabulary: 1,
      total: 5,
    },
    weak_counts: {
      vocabulary: 2,
      grammar: 1,
      sentence_pattern: 1,
    },
    weak_items: {
      success: true,
      vocabulary: [],
      grammar: [],
      sentence_pattern: [],
    },
    suggested_next_lesson: {
      language: 'EN',
      level: 'A2',
      topic: 'Repair grammar: Present Simple',
    },
    today_goal_text: 'Clear 5 due review items, then study: Present Simple.',
    completion_summary: {
      current_streak: 3,
      longest_streak: 5,
      today_completed: false,
      last_active_date: '2026-07-09',
      text: 'Keep your 3-day streak alive with one review.',
    },
  },
})

const mountOptions = {
  global: {
    stubs: {
      StudyBlueprint: true,
      WrongAnswers: true,
      SrsReview: true,
      Archive: true,
    },
  },
}

describe('Progress.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.query = {}
  })

  it('renders progress and streak state from the API', async () => {
    apiMocks.getProgress.mockResolvedValueOnce(progressPayload())

    const wrapper = mount(Progress, mountOptions)
    await flushPromises()

    expect(wrapper.text()).toContain('Careful Learner')
    expect(wrapper.text()).toContain('140')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.get('[data-testid="progress-en-completed"]').text()).toBe(
      '4',
    )
  })

  it('does not crash when the API fails', async () => {
    apiMocks.getProgress.mockRejectedValueOnce(new Error('offline'))

    const wrapper = mount(Progress, mountOptions)
    await flushPromises()

    expect(wrapper.text()).toContain('progress.loadError')
    expect(wrapper.find('button').exists()).toBe(true)
  })
})

describe('Analytics.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders summary and latest versus best accuracy trend labels', async () => {
    apiMocks.getAnalytics.mockResolvedValueOnce(analyticsPayload())

    const wrapper = mount(Analytics)
    await flushPromises()

    expect(wrapper.text()).toContain('140')
    expect(wrapper.text()).toContain('difficult phrase')
    expect(wrapper.text()).toContain('analytics.latestAccuracyValue 75.0')
    expect(wrapper.text()).toContain('analytics.bestAccuracyValue 90.0')
    expect(wrapper.text()).toContain('analytics.bestAccuracyValue 100.0')
    expect(wrapper.text()).toContain('invoice')
    expect(wrapper.text()).toContain('Present Simple')
  })

  it('renders mastery state counts and weakest learning item groups', async () => {
    apiMocks.getAnalytics.mockResolvedValueOnce(analyticsPayload())

    const wrapper = mount(Analytics)
    await flushPromises()

    expect(wrapper.text()).toContain('vocabulary: weak')
    expect(wrapper.text()).toContain('grammar: learning')
    expect(wrapper.text()).toContain('sentence_pattern: review')
    expect(wrapper.text()).toContain('analytics.vocabularyGroup')
    expect(wrapper.text()).toContain('analytics.grammarGroup')
  })

  it('renders recent seven-day learning item review activity', async () => {
    apiMocks.getAnalytics.mockResolvedValueOnce(analyticsPayload())

    const wrapper = mount(Analytics)
    await flushPromises()

    expect(wrapper.text()).toContain('analytics.recentReviewActivity')
    expect(wrapper.text()).toContain('2026-05-11')
    expect(wrapper.text()).toContain('analytics.reviewCount 3')
  })

  it('renders empty data state', async () => {
    apiMocks.getAnalytics.mockResolvedValueOnce(
      analyticsPayload({
        hardest_words: [],
        weakest_category: null,
        accuracy_trend: [],
        mastery_state_counts: {
          vocabulary: {},
          grammar: {},
          sentence_pattern: {},
        },
        weakest_vocabulary: [],
        weakest_grammar: [],
        weakest_sentence_patterns: [],
        recent_7_day_review_counts: [],
      }),
    )

    const wrapper = mount(Analytics)
    await flushPromises()

    expect(wrapper.text()).toContain('analytics.noWrongAnswers')
    expect(wrapper.text()).toContain('analytics.notEnoughData')
    expect(wrapper.text()).toContain('analytics.noReviewHistory')
    expect(wrapper.text()).toContain('analytics.noLearningItemReviewHistory')
  })
})

describe('Materials.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    feedbackMocks.requestConfirmation.mockResolvedValue(true)
  })

  it('renders uploaded RAG materials', async () => {
    apiMocks.listRagMaterials.mockResolvedValueOnce(
      materialsPayload([
        {
          material_id: 'm1',
          doc_id: 'doc-1',
          source: 'notes.txt',
          title: 'Travel Notes',
          language: 'EN',
          source_type: 'text',
          uploaded_at: '2026-05-11T00:00:00',
          total_chunks: 2,
        },
      ]),
    )

    const wrapper = mount(Materials)
    await flushPromises()

    expect(wrapper.text()).toContain('Travel Notes')
    expect(wrapper.text()).toContain('EN')
    expect(wrapper.text()).toContain('2')
  })

  it('uses the embedded language prop and enables upload', async () => {
    apiMocks.listRagMaterials.mockResolvedValueOnce(materialsPayload([]))

    const wrapper = mount(Materials, {
      props: { embedded: true, language: 'EN' },
    })
    await flushPromises()

    expect(wrapper.find('select').exists()).toBe(false)
    expect(wrapper.get('input[type="file"]').attributes('disabled')).toBe(
      undefined,
    )
    expect(apiMocks.listRagMaterials).toHaveBeenCalledWith('EN')
  })

  it('keeps the language selector on the standalone page', async () => {
    apiMocks.listRagMaterials.mockResolvedValueOnce(materialsPayload([]))

    const wrapper = mount(Materials)
    await flushPromises()

    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.get('input[type="file"]').attributes('disabled')).toBe('')
  })

  it('shows backend upload details before falling back to a generic message', async () => {
    apiMocks.listRagMaterials.mockResolvedValue(materialsPayload([]))
    apiMocks.uploadRagMaterial.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'RAG is disabled by configuration' } },
    })

    const wrapper = mount(Materials, {
      props: { embedded: true, language: 'EN' },
    })
    await flushPromises()

    const input = wrapper.get('input[type="file"]').element as HTMLInputElement
    Object.defineProperty(input, 'files', {
      value: [new File(['notes'], 'notes.txt', { type: 'text/plain' })],
      configurable: true,
    })
    await wrapper.get('input[type="file"]').trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('RAG is disabled by configuration')
  })
})

describe('LearningWorkspace.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.query = {}
  })

  it('passes the selected workspace language into embedded Materials', async () => {
    apiMocks.listRagMaterials.mockResolvedValue(materialsPayload([]))

    const wrapper = mount(LearningWorkspace)
    await flushPromises()

    const materials = wrapper.getComponent(Materials)
    expect(materials.props('language')).toBe('EN')

    await wrapper.get('select.workspace-language').setValue('JP')
    await flushPromises()

    expect(wrapper.getComponent(Materials).props('language')).toBe('JP')
  })
})

describe('WrongAnswers.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders wrong answer items', async () => {
    apiMocks.listWrongAnswers.mockResolvedValueOnce(
      wrongAnswersPayload([
        {
          id: 1,
          user_id: 'default_user',
          language: 'EN',
          question_type: 'grammar',
          question: 'I is happy.',
          user_answer: 'is',
          correct_answer: 'am',
          source_lesson_id: 'lesson-1',
          status: 'active',
          wrong_count: 2,
          created_at: '2026-05-11T00:00:00',
          updated_at: '2026-05-11T00:00:00',
        },
      ]),
    )

    const wrapper = mount(WrongAnswers)
    await flushPromises()

    expect(wrapper.text()).toContain('I is happy.')
    expect(wrapper.text()).toContain('am')
  })

  it('can submit a retry action without crashing', async () => {
    const item = {
      id: 1,
      user_id: 'default_user',
      language: 'EN' as const,
      question_type: 'grammar',
      question: 'I is happy.',
      user_answer: 'is',
      correct_answer: 'am',
      source_lesson_id: 'lesson-1',
      status: 'active' as const,
      wrong_count: 1,
      created_at: '2026-05-11T00:00:00',
      updated_at: '2026-05-11T00:00:00',
    }
    const retryResponse: WrongAnswerRetryResponse = {
      success: true,
      correct: false,
      item: { ...item, wrong_count: 2 },
    }
    apiMocks.listWrongAnswers.mockResolvedValueOnce(wrongAnswersPayload([item]))
    apiMocks.retryWrongAnswer.mockResolvedValueOnce(retryResponse)

    const wrapper = mount(WrongAnswers)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'mistakes.retry')
      ?.trigger('click')
    await wrapper
      .find('input[placeholder="mistakes.retryPlaceholder"]')
      .setValue('are')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'mistakes.retrySubmit')
      ?.trigger('click')
    await flushPromises()

    expect(apiMocks.retryWrongAnswer).toHaveBeenCalledWith(1, 'are')
    expect(wrapper.text()).toContain('mistakes.retryIncorrect')
  })
})

describe('TodayLesson.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    feedbackMocks.requestConfirmation.mockResolvedValue(true)
    apiMocks.getMicroToday.mockResolvedValue(microTodayPayload())
    apiMocks.getTodayMission.mockResolvedValue(todayMissionPayload())
    apiMocks.getTts.mockResolvedValue({
      success: true,
      available: false,
      audio_url: null,
      mode: 'preview',
      message:
        'TTS is integration-ready but no runtime provider is configured.',
    })
  })

  it('renders DiagnosticFlow questions before diagnosis is complete', async () => {
    apiMocks.getMicroToday.mockResolvedValueOnce({
      success: true,
      diagnostic_completed: false,
      learning_plan: null,
      lesson: null,
    })
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: null,
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.getDiagnosticQuestions.mockResolvedValueOnce({
      success: true,
      questions: [
        {
          question_id: 'subject-1',
          prompt: 'Which words are the subject?',
          choices: ['The manager', 'checks', 'email'],
          skill: 'subject',
        },
      ],
    })

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(wrapper.get('[data-testid="diagnostic-flow"]').text()).toContain(
      'Which words are the subject?',
    )
  })

  it('renders MicroLesson Day X / Day XX before textbook flow', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(wrapper.get('[data-testid="micro-lesson"]').text()).toContain(
      'microLesson.dayLabel 1 90',
    )
    expect(wrapper.text()).toContain('We raise prices today.')
  })

  it('renders the adaptive today mission panel', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()

    const panel = wrapper.get('[data-testid="today-mission-panel"]')
    expect(panel.text()).toContain('Clear 5 due review items')
    expect(panel.text()).toContain('todayMission.micro.available')
    expect(panel.text()).toContain('5')
    expect(panel.text()).toContain('Repair grammar: Present Simple')
    expect(apiMocks.getTodayMission).toHaveBeenCalledWith('EN')
  })

  it('reloads the language-aware mission and hides English micro lessons on JP', async () => {
    apiMocks.getTodayLesson.mockResolvedValue({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.getTodayMission
      .mockResolvedValueOnce(todayMissionPayload())
      .mockResolvedValueOnce({
        success: true,
        mission: {
          ...todayMissionPayload().mission,
          diagnostic_completed: false,
          micro_lesson_status: 'unavailable',
          learning_plan: null,
          micro_lesson: null,
          due_counts: {
            vocabulary: 0,
            grammar: 1,
            sentence_pattern: 0,
            legacy_vocabulary: 0,
            total: 1,
          },
          weak_counts: {
            vocabulary: 0,
            grammar: 1,
            sentence_pattern: 0,
          },
          suggested_next_lesson: {
            language: 'JP',
            level: 'N5',
            topic: 'Repair grammar: ている',
          },
          today_goal_text:
            "Continue with today's Japanese study: Repair grammar: ている.",
        },
      })

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper.get('select').setValue('JP')
    await flushPromises()

    expect(apiMocks.getTodayMission).toHaveBeenLastCalledWith('JP')
    expect(apiMocks.getMicroToday).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-testid="micro-lesson"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Repair grammar: ている')
  })

  it('marks the micro lesson complete after a correct answer', async () => {
    const completed = microLessonPayload({ completed: true })
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: null,
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.answerMicroLesson.mockResolvedValueOnce({
      success: true,
      correct: true,
      completed: true,
      lesson: completed,
      streak: streak({ today_completed: true }),
    })

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'raise')
      ?.trigger('click')
    await wrapper.get('[data-testid="micro-answer-submit"]').trigger('click')
    await flushPromises()

    expect(apiMocks.answerMicroLesson).toHaveBeenCalledWith('micro-1', 'raise')
    expect(wrapper.get('[data-testid="micro-lesson"]').text()).toContain(
      'microLesson.completed',
    )
    expect(wrapper.get('[data-testid="micro-completed-note"]').text()).toBe(
      'microLesson.completedTodayNote',
    )
  })

  it('shows the next-day unlock note only before the final micro lesson day', async () => {
    const completed = microLessonPayload({
      completed: true,
      day_index: 89,
      total_days: 90,
    })
    apiMocks.getMicroToday.mockResolvedValueOnce(microTodayPayload(completed))
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: null,
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(wrapper.get('[data-testid="micro-completed-note"]').text()).toBe(
      'microLesson.completedTodayNote',
    )
  })

  it('shows a plan-completed note on the final micro lesson day', async () => {
    const completed = microLessonPayload({
      completed: true,
      day_index: 90,
      total_days: 90,
    })
    apiMocks.getMicroToday.mockResolvedValueOnce(microTodayPayload(completed))
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: null,
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(wrapper.get('[data-testid="micro-completed-note"]').text()).toBe(
      'microLesson.planCompletedNote',
    )
  })

  it('shows the fill blank explanation after a wrong micro lesson answer', async () => {
    const lesson = microLessonPayload()
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: null,
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.answerMicroLesson.mockResolvedValueOnce({
      success: true,
      correct: false,
      completed: false,
      lesson,
      streak: streak({ today_completed: false }),
    })

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'raises')
      ?.trigger('click')
    await wrapper.get('[data-testid="micro-answer-submit"]').trigger('click')
    await flushPromises()

    expect(apiMocks.answerMicroLesson).toHaveBeenCalledWith('micro-1', 'raises')
    expect(wrapper.get('[data-testid="micro-answer-explanation"]').text()).toBe(
      'We uses raise.',
    )
  })

  it('renders textbook-style lesson sections', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(wrapper.text()).toContain('hello')
    expect(wrapper.text()).toContain('Use travel greetings.')
    expect(wrapper.text()).toContain('re-')
    expect(wrapper.text()).toContain('I would like ...')
    expect(wrapper.text()).toContain('I ___ a student.')
    expect(wrapper.text()).toContain('I would like tea.')
    expect(wrapper.text()).toContain('A short reading.')
    expect(wrapper.text()).toContain('Hello there')
    expect(wrapper.get('[data-testid="tts-status"]').text()).toContain(
      'TTS is integration-ready but no runtime provider is configured.',
    )
    expect(wrapper.text()).toContain('Explain the cafe greeting.')
    expect(wrapper.text()).toContain('Retake questions.')
  })

  it('shows live TTS state only when the API reports a configured provider', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.getTts.mockResolvedValueOnce({
      success: true,
      available: true,
      audio_url: '/api/audio/audio_123.mp3',
      mode: 'live',
      message: null,
    })

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(apiMocks.getTts).toHaveBeenCalledWith('Hello there.', 'EN')
    expect(wrapper.get('[data-testid="tts-status"]').text()).toContain(
      'lessonSections.immersion.ttsLive',
    )
  })

  it('does not crash when older lesson data omits textbook extension fields', async () => {
    const oldLesson: Partial<Lesson> = lessonPayload()
    delete oldLesson.objectives
    delete oldLesson.word_roots
    delete oldLesson.sentence_patterns
    delete oldLesson.immersion
    delete oldLesson.feynman_prompt
    delete oldLesson.review_plan
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: oldLesson as Lesson,
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()

    expect(wrapper.text()).toContain('hello')
    expect(wrapper.text()).toContain('I ___ a student.')
    expect(wrapper.text()).toContain('A short reading.')
  })

  it('submits selected answers to the review API', async () => {
    const reviewResult: ReviewResult = {
      success: true,
      total_questions: 2,
      correct_count: 2,
      accuracy_rate: 100,
      incorrect_items: [],
      gamification: { xp_added: 20, leveled_up: false },
    }
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.submitReview.mockResolvedValueOnce(reviewResult)

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper.get('[data-testid="grammar-option-0-0"]').setValue()
    await wrapper.get('[data-testid="reading-option-0-0"]').setValue()
    await wrapper.get('[data-testid="submit-review"]').trigger('click')
    await flushPromises()

    expect(apiMocks.submitReview).toHaveBeenCalledWith([
      {
        lesson_id: 'lesson-1',
        exercise_type: 'grammar',
        question_index: 0,
        user_answer: 'am',
        correct_answer: 'am',
      },
      {
        lesson_id: 'lesson-1',
        exercise_type: 'reading',
        question_index: 0,
        user_answer: 'Cafe',
        correct_answer: 'Cafe',
      },
    ])
    expect(wrapper.text()).toContain('today.reviewResult')
  })

  it('shows an in-app notice when submitting without any answers', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper.get('[data-testid="submit-review"]').trigger('click')

    expect(feedbackMocks.showNotice).toHaveBeenCalledWith(
      'today.answerAtLeastOne',
      'warning',
    )
    expect(apiMocks.submitReview).not.toHaveBeenCalled()
  })

  it('blocks partial submit before calling the review API', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper.get('[data-testid="grammar-option-0-0"]').setValue()
    await wrapper.get('[data-testid="submit-review"]').trigger('click')

    expect(feedbackMocks.showNotice).toHaveBeenCalledWith(
      'today.reviewIncomplete 1 2',
      'warning',
    )
    expect(apiMocks.submitReview).not.toHaveBeenCalled()
  })

  it('shows backend review validation details when submit fails', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
    })
    apiMocks.getStreak.mockResolvedValue(streak())
    apiMocks.submitReview.mockRejectedValueOnce({
      isAxiosError: true,
      response: {
        data: {
          error: true,
          message: 'Invalid review payload: missing answers for reading[0]',
          code: 'review_answers_incomplete',
          detail: 'Invalid review payload: missing answers for reading[0]',
        },
      },
    })

    const wrapper = mount(TodayLesson)
    await flushPromises()
    await wrapper.get('[data-testid="grammar-option-0-0"]').setValue()
    await wrapper.get('[data-testid="reading-option-0-0"]').setValue()
    await wrapper.get('[data-testid="submit-review"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain(
      'Invalid review payload: missing answers for reading[0]',
    )
  })
})

describe('Vocabulary.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    feedbackMocks.requestConfirmation.mockResolvedValue(true)
  })

  it('confirms before deleting an imported vocabulary item', async () => {
    apiMocks.listImportedVocabulary.mockResolvedValueOnce({
      success: true,
      count: 1,
      items: [
        {
          id: 7,
          user_id: 'default_user',
          language: 'EN',
          word: 'blocker',
          reading: null,
          definition_zh: 'issue',
          example_sentence: 'We fixed the blocker.',
          example_translation: 'We fixed the issue.',
          created_at: '2026-05-11T00:00:00',
        },
      ],
    })
    apiMocks.deleteImportedVocabulary.mockResolvedValueOnce({ success: true })
    apiMocks.listImportedVocabulary.mockResolvedValueOnce({
      success: true,
      count: 0,
      items: [],
    })

    const wrapper = mount(Vocabulary)
    await flushPromises()
    const buttons = wrapper.findAll('button')
    await buttons[buttons.length - 1]?.trigger('click')
    await flushPromises()

    expect(feedbackMocks.requestConfirmation).toHaveBeenCalled()
    expect(apiMocks.deleteImportedVocabulary).toHaveBeenCalledWith(7)
  })

  it('renders root and category review fields for imported vocabulary', async () => {
    apiMocks.listImportedVocabulary.mockResolvedValueOnce({
      success: true,
      count: 1,
      items: [
        {
          id: 8,
          user_id: 'default_user',
          language: 'EN',
          word: 'review',
          reading: null,
          definition_zh: '複習',
          example_sentence: 'I review words.',
          example_translation: '我複習單字。',
          part_of_speech: 'verb',
          root: 'view',
          prefix: 're-',
          suffix: null,
          memory_tip: 're- means again.',
          category: 'study',
          tags: ['root', 'habit'],
          created_at: '2026-05-11T00:00:00',
        },
      ],
    })

    const wrapper = mount(Vocabulary)
    await flushPromises()

    expect(wrapper.text()).toContain('POS: verb')
    expect(wrapper.text()).toContain('Root: view')
    expect(wrapper.text()).toContain('Prefix: re-')
    expect(wrapper.text()).toContain('Tip: re- means again.')
    expect(wrapper.text()).toContain('Category: study')
    expect(wrapper.text()).toContain('Tags: root, habit')
  })
})
