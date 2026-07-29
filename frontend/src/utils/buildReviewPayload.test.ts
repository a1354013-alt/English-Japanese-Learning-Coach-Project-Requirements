import { describe, expect, it } from 'vitest'
import type { Lesson } from '@/types'
import { buildReviewPayload } from '@/utils/buildReviewPayload'

describe('buildReviewPayload', () => {
  it('builds a review payload from lesson + selected answers', () => {
    const lesson = {
      metadata: {
        lesson_id: 'l1',
        language: 'EN',
        level: 'A1',
        topic: 'T',
        generated_at: '2026-04-22T00:00:00Z',
        estimated_duration_minutes: 5,
        key_points: [],
      },
      vocabulary: [],
      grammar: {
        title: 'G',
        explanation: 'E',
        examples: [],
        exercises: [
          {
            question: 'q1',
            options: ['A', 'B'],
            correct_answer: 'A',
            explanation: 'x',
          },
          {
            question: 'q2',
            options: ['C', 'D'],
            correct_answer: 'D',
            explanation: 'y',
          },
        ],
      },
      reading: {
        title: 'R',
        content: 'C',
        word_count: 1,
        questions: [
          {
            question: 'rq1',
            options: ['X', 'Y'],
            correct_answer: 'Y',
            explanation: 'z',
          },
        ],
      },
      dialogue: { scenario: 'S', context: 'C', dialogue: [], alternatives: [] },
    } as unknown as Lesson

    const payload = buildReviewPayload(lesson, {
      grammar: { 0: 'A', 1: '   ' },
      reading: { 0: 'X' },
    })

    expect(payload).toEqual([
      {
        lesson_id: 'l1',
        exercise_type: 'grammar',
        question_index: 0,
        user_answer: 'A',
        correct_answer: 'A',
      },
      {
        lesson_id: 'l1',
        exercise_type: 'reading',
        question_index: 0,
        user_answer: 'X',
        correct_answer: 'Y',
      },
    ])
  })

  it('adds the stable client submission id to every answer when provided', () => {
    const lesson = {
      metadata: {
        lesson_id: 'l1',
        language: 'EN',
        level: 'A1',
        topic: 'T',
        generated_at: '2026-04-22T00:00:00Z',
        estimated_duration_minutes: 5,
        key_points: [],
      },
      vocabulary: [],
      grammar: {
        title: 'G',
        explanation: 'E',
        examples: [],
        exercises: [
          {
            question: 'q1',
            options: ['A', 'B'],
            correct_answer: 'A',
            explanation: 'x',
          },
        ],
      },
      reading: {
        title: 'R',
        content: 'C',
        word_count: 1,
        questions: [
          {
            question: 'rq1',
            options: ['X', 'Y'],
            correct_answer: 'Y',
            explanation: 'z',
          },
        ],
      },
      dialogue: { scenario: 'S', context: 'C', dialogue: [], alternatives: [] },
    } as unknown as Lesson

    const payload = buildReviewPayload(
      lesson,
      {
        grammar: { 0: 'A' },
        reading: { 0: 'Y' },
      },
      'review-client-1',
    )

    expect(payload.map((item) => item.client_submission_id)).toEqual([
      'review-client-1',
      'review-client-1',
    ])
  })
})
