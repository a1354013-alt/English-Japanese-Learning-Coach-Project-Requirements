import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SrsReview from '@/views/SrsReview.vue'

const apiMocks = vi.hoisted(() => ({
  getDueLearningItems: vi.fn(),
  submitLearningItemReview: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
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

  it('renders item-level metadata and a safe fallback when due_at is present', async () => {
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
    expect(wrapper.text()).toContain('learning')
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
      correct: false,
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
