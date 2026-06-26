import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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

const flushPromises = () =>
  new Promise((resolve) => window.setTimeout(resolve, 0))

describe('SrsReview.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

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

  it('submits each item with its own language instead of the current filter', async () => {
    apiMocks.getDueSrs.mockResolvedValue({
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
        {
          word: 'こんにちは',
          language: 'JP',
          definition_zh: 'hello',
          next_review: null,
          interval: 1,
          ease_factor: 2.5,
          srs_level: 0,
        },
      ],
    })
    apiMocks.submitSrsReview.mockResolvedValue({ success: true })

    const wrapper = mount(SrsReview)
    await flushPromises()

    const buttons = wrapper.findAll('button')
    await buttons[1]?.trigger('click')
    await flushPromises()
    await buttons[4]?.trigger('click')
    await flushPromises()

    expect(apiMocks.submitSrsReview).toHaveBeenNthCalledWith(
      1,
      'hello',
      'EN',
      5,
    )
    expect(apiMocks.submitSrsReview).toHaveBeenNthCalledWith(
      2,
      'こんにちは',
      'JP',
      5,
    )
  })

  it('keeps the original item language after the dropdown switches', async () => {
    apiMocks.getDueSrs.mockResolvedValue({
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
    apiMocks.submitSrsReview.mockResolvedValue({ success: true })

    const wrapper = mount(SrsReview)
    await flushPromises()

    await wrapper.get('select').setValue('JP')
    await flushPromises()
    await wrapper.findAll('button')[1]?.trigger('click')
    await flushPromises()

    expect(apiMocks.submitSrsReview).toHaveBeenCalledWith('hello', 'EN', 5)
  })
})
