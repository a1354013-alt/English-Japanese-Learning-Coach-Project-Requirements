import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SrsReview from '@/views/SrsReview.vue'

const apiMocks = vi.hoisted(() => ({
  getDueLearningItems: vi.fn(),
  submitLearningItemReview: vi.fn(),
}))

const translationMap: Record<string, string> = {
  'review.itemTypeLabels.vocabulary': 'Vocabulary',
  'review.itemTypeLabels.grammar': 'Grammar',
  'review.itemTypeLabels.sentence_pattern': 'Sentence Pattern',
  'review.masteryStateLabels.new': 'New',
  'review.masteryStateLabels.learning': 'Learning',
  'review.masteryStateLabels.review': 'Review',
  'review.masteryStateLabels.weak': 'Weak',
  'review.masteryStateLabels.mastered': 'Mastered',
}

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => translationMap[key] ?? key,
  }),
}))

vi.mock('@/services/api', () => ({
  reviewApi: {
    getDueLearningItems: apiMocks.getDueLearningItems,
    submitLearningItemReview: apiMocks.submitLearningItemReview,
  },
}))

const flushPromises = () =>
  new Promise((resolve) => window.setTimeout(resolve, 0))

describe('SrsReview.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders friendly item labels alongside item-level metadata', async () => {
    apiMocks.getDueLearningItems.mockResolvedValueOnce({
      success: true,
      items: [
        {
          item_id: 'item-1',
          item_type: 'vocabulary',
          item_key: 'hello',
          language: 'EN',
          content: { definition_zh: 'greeting' },
          root: 'hel',
          memory_tip: 'Picture greeting a friend.',
          category: 'speaking',
          tags: ['daily'],
          mastery_state: 'learning',
          due_at: '2026-05-11T00:00:00',
        },
      ],
    })

    const wrapper = mount(SrsReview)
    await flushPromises()

    expect(wrapper.text()).toContain('hello')
    expect(wrapper.text()).toContain('Picture greeting a friend.')
    expect(wrapper.text()).toContain('speaking')
    expect(wrapper.text()).toContain('root: hel')
    expect(wrapper.text()).toContain('tags: daily')
    expect(wrapper.text()).toContain('Vocabulary / Learning')
    expect(wrapper.text()).not.toContain('vocabulary / learning')
  })

  it('submits item-level ratings with the item id', async () => {
    apiMocks.getDueLearningItems.mockResolvedValue({
      success: true,
      items: [
        {
          item_id: 'item-en',
          item_type: 'vocabulary',
          item_key: 'hello',
          language: 'EN',
          content: { definition_zh: 'greeting' },
          tags: [],
          mastery_state: 'new',
          due_at: '2026-05-11T00:00:00',
        },
      ],
    })
    apiMocks.submitLearningItemReview.mockResolvedValue({ success: true })

    const wrapper = mount(SrsReview)
    await flushPromises()

    const buttons = wrapper.findAll('button')
    await buttons[1]?.trigger('click')
    await flushPromises()

    expect(apiMocks.submitLearningItemReview).toHaveBeenCalledWith({
      item_id: 'item-en',
      rating: 0,
      source: 'srs_review',
    })
  })

  it('reloads when the item type filter changes', async () => {
    apiMocks.getDueLearningItems.mockResolvedValue({
      success: true,
      items: [],
    })

    const wrapper = mount(SrsReview)
    await flushPromises()

    const selects = wrapper.findAll('select')
    await selects[1]?.setValue('grammar')
    await flushPromises()

    expect(apiMocks.getDueLearningItems).toHaveBeenLastCalledWith({
      language: 'EN',
      item_type: 'grammar',
    })
  })
})
