<template>
  <section class="grid" style="margin-top: 1rem" data-testid="today-lesson">
    <div class="panel row between center">
      <div>
        <h2 style="margin: 0" data-testid="today-lesson-title">Today's Lesson</h2>
        <p style="margin: 0.2rem 0 0">{{ lesson?.metadata.topic || 'No lesson generated yet' }}</p>
        <p v-if="streak" style="margin: 0.2rem 0 0; color: #475569">
          🔥 Study streak: {{ streak.current_streak }} days (best {{ streak.longest_streak }}) · Completed today: {{ streak.today_completed ? 'Yes' : 'No' }}
        </p>
      </div>
      <div class="row gap-sm">
        <select v-model="request.language">
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
        <button @click="loadTodayLesson" class="secondary">Refresh</button>
      </div>
    </div>

    <!-- Loading State -->
    <div class="panel" v-if="loading && !lesson">
      <p>Loading today's lesson...</p>
    </div>

    <!-- Error State -->
    <div class="panel" v-else-if="error && !lesson">
      <p style="color: #d32f2f">{{ error }}</p>
      <button @click="loadTodayLesson" class="secondary">Retry</button>
    </div>

    <!-- Empty State - Generate Lesson -->
    <div class="panel grid" v-if="!lesson && !loading && !error" data-testid="generate-panel">
      <h3>Generate lesson</h3>
      <input v-model="request.topic" placeholder="Optional topic" data-testid="generate-topic" />
      <select v-model="request.difficulty">
        <option v-for="level in currentLevels" :key="level" :value="level">{{ level }}</option>
      </select>
      <button data-testid="generate-button" :disabled="loadingGenerate" @click="generateLesson">{{ loadingGenerate ? 'Generating...' : 'Generate' }}</button>
    </div>

    <!-- Lesson Content -->
    <div v-else class="grid">
      <div class="panel" data-testid="lesson-vocabulary">
        <h3>Vocabulary</h3>
        <ul>
          <li v-for="(item, idx) in lesson?.vocabulary" :key="`${item.word}-${idx}`">
            <strong>{{ item.word }}</strong>
            <span v-if="item.reading"> ({{ item.reading }})</span>
            <span v-if="item.phonetic"> ({{ item.phonetic }})</span>
            <div>{{ item.definition_zh }}</div>
            <small>{{ item.example_sentence }} / {{ item.example_translation }}</small>
          </li>
        </ul>
      </div>

      <div class="panel" data-testid="lesson-grammar">
        <h3>Grammar Exercises</h3>
        <div
          v-for="(exercise, index) in lesson?.grammar.exercises"
          :key="`g-${index}`"
          class="panel"
          style="margin-top: 0.75rem"
          :data-testid="`grammar-exercise-${index}`"
        >
          <p><strong>{{ index + 1 }}. {{ exercise.question }}</strong></p>
          <div class="grid" v-if="exercise.options?.length">
            <label v-for="(option, optionIndex) in exercise.options" :key="option" class="row gap-sm center">
              <input
                type="radio"
                :name="`g-${index}`"
                :value="option"
                v-model="answers.grammar[index]"
                :data-testid="`grammar-option-${index}-${optionIndex}`"
              />
              <span>{{ option }}</span>
            </label>
          </div>
          <input v-else v-model="answers.grammar[index]" placeholder="Your answer" :data-testid="`grammar-input-${index}`" />
        </div>
      </div>

      <div class="panel" data-testid="lesson-reading">
        <h3>Reading</h3>
        <p style="white-space: pre-wrap">{{ lesson?.reading.content }}</p>
        <div
          v-for="(question, index) in lesson?.reading.questions"
          :key="`r-${index}`"
          class="panel"
          style="margin-top: 0.75rem"
          :data-testid="`reading-question-${index}`"
        >
          <p><strong>{{ index + 1 }}. {{ question.question }}</strong></p>
          <div class="grid">
            <label v-for="(option, optionIndex) in question.options" :key="option" class="row gap-sm center">
              <input
                type="radio"
                :name="`r-${index}`"
                :value="option"
                v-model="answers.reading[index]"
                :data-testid="`reading-option-${index}-${optionIndex}`"
              />
              <span>{{ option }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="panel row gap-sm center">
        <button data-testid="submit-review" :disabled="submitting" @click="submitReview">{{ submitting ? 'Submitting...' : 'Submit Review' }}</button>
        <button class="secondary" @click="exportPdf">Export PDF</button>
      </div>

      <!-- Success State - Review Result -->
      <div class="panel" v-if="reviewResult" data-testid="review-result">
        <h3>Review Result</h3>
        <p data-testid="review-score">Score: {{ reviewResult.correct_count }} / {{ reviewResult.total_questions }} ({{ reviewResult.accuracy_rate.toFixed(1) }}%)</p>
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
import { lessonApi, reviewApi, streakApi } from '@/services/api'
import type { Language, Lesson, ReviewResult, StreakResponse } from '@/types'
import { buildReviewPayload } from '@/utils/buildReviewPayload'

const request = reactive<{ language: Language; topic: string; difficulty: string }>({
  language: 'EN',
  topic: '',
  difficulty: 'A1',
})

const lesson = ref<Lesson | null>(null)
const loading = ref(false)
const loadingGenerate = ref(false)
const error = ref<string | null>(null)
const submitting = ref(false)
const reviewResult = ref<ReviewResult | null>(null)
const streak = ref<StreakResponse | null>(null)

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
  error.value = null
  try {
    const res = await lessonApi.getTodayLesson(request.language)
    lesson.value = res.lesson
    resetAnswers()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load today\'s lesson'
  } finally {
    loading.value = false
  }
}

const loadStreak = async () => {
  try {
    streak.value = await streakApi.getStreak()
  } catch {
    streak.value = null
  }
}

const generateLesson = async () => {
  loadingGenerate.value = true
  error.value = null
  try {
    const res = await lessonApi.generateLesson({
      language: request.language,
      topic: request.topic || undefined,
      difficulty: request.difficulty,
    })
    lesson.value = res.lesson
    resetAnswers()
    await loadStreak()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to generate lesson'
  } finally {
    loadingGenerate.value = false
  }
}

const submitReview = async () => {
  if (!lesson.value) {
    return
  }
  const payload = buildReviewPayload(lesson.value, answers)
  if (payload.length === 0) {
    return
  }

  submitting.value = true
  try {
    reviewResult.value = await reviewApi.submitReview(payload)
    await loadStreak()
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
onMounted(loadStreak)
</script>
