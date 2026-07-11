import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FeynmanSection from '@/components/lesson/FeynmanSection.vue'

const apiMocks = vi.hoisted(() => ({
  submitFeynmanFeedback: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, string | number>) =>
      params ? `${key} ${Object.values(params).join(' ')}` : key,
  }),
}))

vi.mock('@/services/api', () => ({
  lessonApi: {
    submitFeynmanFeedback: apiMocks.submitFeynmanFeedback,
  },
}))

const flushPromises = () =>
  new Promise((resolve) => window.setTimeout(resolve, 0))

describe('FeynmanSection.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the prompt and checklist', () => {
    const wrapper = mount(FeynmanSection, {
      props: {
        lessonId: 'lesson-1',
        language: 'EN',
        feynman: {
          prompt: 'Explain the lesson.',
          checklist: ['Use one example.'],
        },
      },
    })

    expect(wrapper.text()).toContain('Explain the lesson.')
    expect(wrapper.text()).toContain('Use one example.')
  })

  it('submits the explanation and shows feedback', async () => {
    apiMocks.submitFeynmanFeedback.mockResolvedValueOnce({
      success: true,
      feedback: {
        summary: 'Clear explanation.',
        strengths: ['Used the core vocabulary.'],
        missing_points: ['Add one more example.'],
        corrections: ['Make the grammar point more explicit.'],
        suggested_simple_explanation: 'This lesson practices one key pattern.',
        related_weak_items: ['review'],
        score: 82,
      },
    })

    const wrapper = mount(FeynmanSection, {
      props: {
        lessonId: 'lesson-1',
        language: 'EN',
        feynman: {
          prompt: 'Explain the lesson.',
          checklist: ['Use one example.'],
        },
      },
    })

    await wrapper
      .get('[data-testid="feynman-input"]')
      .setValue('My explanation')
    await wrapper.get('[data-testid="feynman-submit"]').trigger('click')
    await flushPromises()

    expect(apiMocks.submitFeynmanFeedback).toHaveBeenCalledWith('lesson-1', {
      explanation: 'My explanation',
      language: 'EN',
    })
    expect(wrapper.get('[data-testid="feynman-feedback"]').text()).toContain(
      'Clear explanation.',
    )
    expect(wrapper.text()).toContain('lessonSections.feynman.score 82')
  })

  it('handles API failure with an inline error state', async () => {
    apiMocks.submitFeynmanFeedback.mockRejectedValueOnce(new Error('offline'))

    const wrapper = mount(FeynmanSection, {
      props: {
        lessonId: 'lesson-1',
        language: 'EN',
        feynman: {
          prompt: 'Explain the lesson.',
          checklist: [],
        },
      },
    })

    await wrapper
      .get('[data-testid="feynman-input"]')
      .setValue('My explanation')
    await wrapper.get('[data-testid="feynman-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="feynman-error"]').text()).toContain(
      'lessonSections.feynman.error',
    )
  })
})
