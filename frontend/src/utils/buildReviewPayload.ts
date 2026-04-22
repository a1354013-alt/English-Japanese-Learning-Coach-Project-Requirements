import type { Lesson, ReviewAnswer } from '@/types'

export type ReviewAnswerDraft = {
  grammar: Record<number, string>
  reading: Record<number, string>
}

export function buildReviewPayload(lesson: Lesson, answers: ReviewAnswerDraft): ReviewAnswer[] {
  const payload: ReviewAnswer[] = []

  lesson.grammar.exercises.forEach((exercise, index) => {
    const userAnswer = answers.grammar[index]
    if (typeof userAnswer === 'string' && userAnswer.trim().length > 0) {
      payload.push({
        lesson_id: lesson.metadata.lesson_id,
        exercise_type: 'grammar',
        question_index: index,
        user_answer: userAnswer,
        correct_answer: exercise.correct_answer,
      })
    }
  })

  lesson.reading.questions.forEach((question, index) => {
    const userAnswer = answers.reading[index]
    if (typeof userAnswer === 'string' && userAnswer.trim().length > 0) {
      payload.push({
        lesson_id: lesson.metadata.lesson_id,
        exercise_type: 'reading',
        question_index: index,
        user_answer: userAnswer,
        correct_answer: question.correct_answer,
      })
    }
  })

  return payload
}

