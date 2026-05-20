import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Analytics from '@/views/Analytics.vue'
import Materials from '@/views/Materials.vue'
import Progress from '@/views/Progress.vue'
import TodayLesson from '@/views/TodayLesson.vue'
import Vocabulary from '@/views/Vocabulary.vue'
import WrongAnswers from '@/views/WrongAnswers.vue'
import type {
  AnalyticsResponse,
  Language,
  Lesson,
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
  submitReview: vi.fn(),
  getStreak: vi.fn(),
  resetDemo: vi.fn(),
  exportPdf: vi.fn(),
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
    hardest_words: [{ word: 'こんにちは', mistakes: 2 }],
    weakest_category: { category: 'grammar', active_items: 1 },
    accuracy_trend: [
      {
        lesson_id: null,
        accuracy_rate: 75,
        submitted_at: '2026-05-10T00:00:00',
      },
      {
        lesson_id: 'lesson-2',
        accuracy_rate: 100,
        submitted_at: '2026-05-11T00:00:00',
      },
    ],
    today_completed: true,
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
  vocabulary: [
    {
      word: 'hello',
      phonetic: 'həˈloʊ',
      definition_zh: 'greeting',
      example_sentence: 'Hello there.',
      example_translation: '你好。',
    },
  ],
  grammar: {
    title: 'Be verbs',
    explanation: 'Use am/is/are.',
    examples: [],
    exercises: [
      {
        question: 'I ___ a student.',
        options: ['am', 'is'],
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
        options: ['Cafe', 'Station'],
        correct_answer: 'Cafe',
        explanation: 'The passage says cafe.',
      },
    ],
  },
  dialogue: {
    scenario: 'Cafe',
    context: 'Ordering',
    dialogue: [],
    alternatives: [],
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

  it('renders summary and trend points, including nullable lesson_id records', async () => {
    apiMocks.getAnalytics.mockResolvedValueOnce(analyticsPayload())

    const wrapper = mount(Analytics)
    await flushPromises()

    expect(wrapper.text()).toContain('140')
    expect(wrapper.text()).toContain('こんにちは')
    expect(wrapper.text()).toContain('75.0%')
    expect(wrapper.text()).toContain('100.0%')
  })

  it('renders empty data state', async () => {
    apiMocks.getAnalytics.mockResolvedValueOnce(
      analyticsPayload({
        hardest_words: [],
        weakest_category: null,
        accuracy_trend: [],
      }),
    )

    const wrapper = mount(Analytics)
    await flushPromises()

    expect(wrapper.text()).toContain('analytics.noWrongAnswers')
    expect(wrapper.text()).toContain('analytics.notEnoughData')
    expect(wrapper.text()).toContain('analytics.noReviewHistory')
  })

  it('renders loading and error states', async () => {
    apiMocks.getAnalytics.mockImplementationOnce(
      () => new Promise(() => undefined),
    )
    const loadingWrapper = mount(Analytics)
    expect(loadingWrapper.text()).toContain('analytics.loading')

    apiMocks.getAnalytics.mockRejectedValueOnce(new Error('offline'))
    const errorWrapper = mount(Analytics)
    await flushPromises()
    expect(errorWrapper.text()).toContain('analytics.loadError')
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

  it('renders empty state when RAG has no materials', async () => {
    apiMocks.listRagMaterials.mockResolvedValueOnce(materialsPayload([]))

    const wrapper = mount(Materials)
    await flushPromises()

    expect(wrapper.text()).toContain('materials.empty')
  })

  it('renders API error state without crashing', async () => {
    apiMocks.listRagMaterials.mockRejectedValueOnce(
      new Error('rag unavailable'),
    )

    const wrapper = mount(Materials)
    await flushPromises()

    expect(wrapper.text()).toContain('materials.loadError')
  })

  it('confirms before deleting a material', async () => {
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
    apiMocks.deleteRagMaterial.mockResolvedValueOnce({ success: true })
    apiMocks.listRagMaterials.mockResolvedValueOnce(materialsPayload([]))

    const wrapper = mount(Materials)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'materials.delete')
      ?.trigger('click')
    await flushPromises()

    expect(feedbackMocks.requestConfirmation).toHaveBeenCalled()
    expect(apiMocks.deleteRagMaterial).toHaveBeenCalledWith('doc-1')
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

  it('renders empty state', async () => {
    apiMocks.listWrongAnswers.mockResolvedValueOnce(wrongAnswersPayload([]))

    const wrapper = mount(WrongAnswers)
    await flushPromises()

    expect(wrapper.text()).toContain('mistakes.empty')
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
  })

  it('renders vocabulary, grammar, and reading sections', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: lessonPayload(),
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

  it('renders no lesson and error states', async () => {
    apiMocks.getTodayLesson.mockResolvedValueOnce({
      success: true,
      lesson: null,
    })
    apiMocks.getStreak.mockResolvedValue(streak({ today_completed: false }))
    const emptyWrapper = mount(TodayLesson)
    await flushPromises()
    expect(emptyWrapper.find('[data-testid="generate-panel"]').exists()).toBe(
      true,
    )

    apiMocks.getTodayLesson.mockRejectedValueOnce(new Error('offline'))
    const errorWrapper = mount(TodayLesson)
    await flushPromises()
    expect(errorWrapper.text()).toContain('today.loadError')
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
          definition_zh: '阻礙',
          example_sentence: 'We fixed the blocker.',
          example_translation: '我們解掉阻礙了。',
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
})
