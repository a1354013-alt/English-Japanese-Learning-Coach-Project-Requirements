import type { Lesson, ReviewAnswer } from '@/types'

export type ReviewAnswerDraft = {
  grammar: Record<number, string>
  reading: Record<number, string>
}

export function buildReviewPayload(
  lesson: Lesson,
  answers: ReviewAnswerDraft,
  clientSubmissionId?: string,
): ReviewAnswer[] {
  const payload: ReviewAnswer[] = []

  lesson.grammar.exercises.forEach((exercise, index) => {
    const userAnswer = answers.grammar[index]
    if (typeof userAnswer === 'string' && userAnswer.trim().length > 0) {
      const item: ReviewAnswer = {
        lesson_id: lesson.metadata.lesson_id,
        exercise_type: 'grammar',
        question_index: index,
        user_answer: userAnswer,
        correct_answer: exercise.correct_answer,
      }
      if (clientSubmissionId) item.client_submission_id = clientSubmissionId
      payload.push(item)
    }
  })

  lesson.reading.questions.forEach((question, index) => {
    const userAnswer = answers.reading[index]
    if (typeof userAnswer === 'string' && userAnswer.trim().length > 0) {
      const item: ReviewAnswer = {
        lesson_id: lesson.metadata.lesson_id,
        exercise_type: 'reading',
        question_index: index,
        user_answer: userAnswer,
        correct_answer: question.correct_answer,
      }
      if (clientSubmissionId) item.client_submission_id = clientSubmissionId
      payload.push(item)
    }
  })

  return payload
}
