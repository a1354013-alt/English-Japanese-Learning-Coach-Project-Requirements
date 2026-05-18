import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import SrsReview from '@/views/SrsReview.vue'

const apiMocks = vi.hoisted(() => ({
  getDueSrs: vi.fn(),
  submitSrsReview: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/services/api', () => ({
  reviewApi: {
    getDueSrs: apiMocks.getDueSrs,
    submitSrsReview: apiMocks.submitSrsReview,
  },
}))

const flushPromises = () => new Promise((resolve) => window.setTimeout(resolve, 0))

describe('SrsReview.vue', () => {
  it('renders a safe fallback when next_review is null', async () => {
    apiMocks.getDueSrs.mockResolvedValueOnce({
      success: true,
      items: [
        {
          word: 'hello',
          language: 'EN',
          definition_zh: 'greeting',
          next_review: null,
          interval: 1,
          ease_factor: 2.5,
          srs_level: 0,
        },
      ],
    })

    const wrapper = mount(SrsReview)
    await flushPromises()

    expect(wrapper.text()).toContain('hello')
    expect(wrapper.text()).toContain('-')
  })
})
