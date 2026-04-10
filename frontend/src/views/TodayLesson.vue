<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <div>
        <h2 style="margin: 0">Today's Lesson</h2>
        <p style="margin: 0.2rem 0 0">{{ lesson?.metadata.topic || 'No lesson generated yet' }}</p>
      </div>
      <div class="row gap-sm">
        <select v-model="request.language">
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
        <button @click="loadTodayLesson" class="secondary">Refresh</button>
      </div>
    </div>

    <div class="panel grid" v-if="!lesson">
      <h3>Generate lesson</h3>
      <input v-model="request.topic" placeholder="Optional topic" />
      <select v-model="request.difficulty">
        <option v-for="level in currentLevels" :key="level" :value="level">{{ level }}</option>
      </select>
      <button :disabled="loading" @click="generateLesson">{{ loading ? 'Generating...' : 'Generate' }}</button>
    </div>

    <div v-else class="grid">
      <div class="panel">
        <h3>Vocabulary</h3>
        <ul>
          <li v-for="(item, idx) in lesson.vocabulary" :key="`${item.word}-${idx}`">
            <strong>{{ item.word }}</strong>
            <span v-if="item.reading"> ({{ item.reading }})</span>
            <span v-if="item.phonetic"> ({{ item.phonetic }})</span>
            <div>{{ item.definition_zh }}</div>
            <small>{{ item.example_sentence }} / {{ item.example_translation }}</small>
          </li>
        </ul>
      </div>

      <div class="panel">
        <h3>Grammar Exercises</h3>
        <div v-for="(exercise, index) in lesson.grammar.exercises" :key="`g-${index}`" class="panel" style="margin-top: 0.75rem">
          <p><strong>{{ index + 1 }}. {{ exercise.question }}</strong></p>
          <div class="grid" v-if="exercise.options?.length">
            <label v-for="option in exercise.options" :key="option" class="row gap-sm center">
              <input type="radio" :name="`g-${index}`" :value="option" v-model="answers.grammar[index]" />
              <span>{{ option }}</span>
            </label>
          </div>
          <input v-else v-model="answers.grammar[index]" placeholder="Your answer" />
        </div>
      </div>

      <div class="panel">
        <h3>Reading</h3>
        <p style="white-space: pre-wrap">{{ lesson.reading.content }}</p>
        <div v-for="(question, index) in lesson.reading.questions" :key="`r-${index}`" class="panel" style="margin-top: 0.75rem">
          <p><strong>{{ index + 1 }}. {{ question.question }}</strong></p>
          <div class="grid">
            <label v-for="option in question.options" :key="option" class="row gap-sm center">
              <input type="radio" :name="`r-${index}`" :value="option" v-model="answers.reading[index]" />
              <span>{{ option }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="panel row gap-sm center">
        <button :disabled="submitting" @click="submitReview">{{ submitting ? 'Submitting...' : 'Submit Review' }}</button>
        <button class="secondary" @click="exportPdf">Export PDF</button>
      </div>

      <div class="panel" v-if="reviewResult">
        <h3>Review Result</h3>
        <p>Score: {{ reviewResult.correct_count }} / {{ reviewResult.total_questions }} ({{ reviewResult.accuracy_rate.toFixed(1) }}%)</p>
        <ul v-if="reviewResult.incorrect_items.length">
          <li v-for="(item, idx) in reviewResult.incorrect_items" :key="idx">
            {{ item.question }} - Correct: {{ item.correct_answer }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { lessonApi, reviewApi } from '@/services/api'
import type { Language, Lesson, ReviewAnswer, ReviewResult } from '@/types'

const request = reactive<{ language: Language; topic: string; difficulty: string }>({
  language: 'EN',
  topic: '',
  difficulty: 'A1',
})

const lesson = ref<Lesson | null>(null)
const loading = ref(false)
const submitting = ref(false)
const reviewResult = ref<ReviewResult | null>(null)

const answers = reactive<{ grammar: Record<number, string>; reading: Record<number, string> }>({
  grammar: {},
  reading: {},
})

const currentLevels = computed(() => (request.language === 'EN' ? ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] : ['N5', 'N4', 'N3', 'N2', 'N1']))

const resetAnswers = () => {
  answers.grammar = {}
  answers.reading = {}
  reviewResult.value = null
}

const loadTodayLesson = async () => {
  loading.value = true
  try {
    const res = await lessonApi.getTodayLesson(request.language)
    lesson.value = res.lesson
    resetAnswers()
  } finally {
    loading.value = false
  }
}

const generateLesson = async () => {
  loading.value = true
  try {
    const res = await lessonApi.generateLesson({
      language: request.language,
      topic: request.topic || undefined,
      difficulty: request.difficulty,
    })
    lesson.value = res.lesson
    resetAnswers()
  } finally {
    loading.value = false
  }
}

const collectAnswers = (): ReviewAnswer[] => {
  if (!lesson.value) {
    return []
  }

  const payload: ReviewAnswer[] = []
  lesson.value.grammar.exercises.forEach((exercise, index) => {
    const userAnswer = answers.grammar[index]
    if (typeof userAnswer === 'string' && userAnswer.trim().length > 0) {
      payload.push({
        lesson_id: lesson.value!.metadata.lesson_id,
        exercise_type: 'grammar',
        question_index: index,
        user_answer: userAnswer,
        correct_answer: exercise.correct_answer,
      })
    }
  })

  lesson.value.reading.questions.forEach((question, index) => {
    const userAnswer = answers.reading[index]
    if (typeof userAnswer === 'string' && userAnswer.trim().length > 0) {
      payload.push({
        lesson_id: lesson.value!.metadata.lesson_id,
        exercise_type: 'reading',
        question_index: index,
        user_answer: userAnswer,
        correct_answer: question.correct_answer,
      })
    }
  })

  return payload
}

const submitReview = async () => {
  const payload = collectAnswers()
  if (payload.length === 0) {
    return
  }

  submitting.value = true
  try {
    reviewResult.value = await reviewApi.submitReview(payload)
  } finally {
    submitting.value = false
  }
}

const exportPdf = () => {
  if (lesson.value) {
    lessonApi.exportPdf(lesson.value.metadata.lesson_id)
  }
}

watch(
  () => request.language,
  () => {
    request.difficulty = request.language === 'EN' ? 'A1' : 'N5'
    void loadTodayLesson()
  },
)

onMounted(loadTodayLesson)
</script>
