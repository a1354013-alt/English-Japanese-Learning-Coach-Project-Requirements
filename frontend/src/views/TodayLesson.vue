<template>
  <section class="page-shell page-stack" data-testid="today-lesson">
    <div class="hero-card today-hero">
      <div class="page-header">
        <div>
          <span class="page-eyebrow">{{ t('today.eyebrow') }}</span>
          <h1 class="page-title" data-testid="today-lesson-title">{{ t('today.title') }}</h1>
          <p class="page-subtitle">
            {{ lesson?.metadata.topic || t('today.noLesson') }}
          </p>
        </div>

        <div class="toolbar today-toolbar">
          <select v-model="request.language" :aria-label="t('common.language')">
            <option value="EN">{{ t('common.english') }}</option>
            <option value="JP">{{ t('common.japanese') }}</option>
          </select>
          <button type="button" class="secondary" @click="resetDemo" :disabled="resettingDemo">
            {{ resettingDemo ? t('today.resettingDemo') : t('today.resetDemo') }}
          </button>
          <button type="button" class="secondary" @click="loadTodayLesson">
            {{ t('common.refresh') }}
          </button>
        </div>
      </div>

      <div v-if="lesson" class="content-grid-2 today-summary-grid">
        <div class="surface-muted summary-card">
          <h2>{{ t('today.summaryTitle') }}</h2>
          <p class="summary-meta">
            {{ lesson.metadata.language }} · {{ lesson.metadata.level }} ·
            {{ t('today.estimatedDuration', { minutes: lesson.metadata.estimated_duration_minutes }) }}
          </p>
          <div class="summary-pills">
            <span v-for="(point, index) in lesson.metadata.key_points" :key="`${point}-${index}`" class="summary-pill">
              {{ point }}
            </span>
          </div>
        </div>

        <div class="surface-muted summary-card">
          <h2>{{ t('today.todayStatus') }}</h2>
          <div class="summary-list">
            <div class="summary-list-item">
              <span>{{ t('today.studyLanguage') }}</span>
              <strong>{{ request.language }}</strong>
            </div>
            <div class="summary-list-item">
              <span>{{ t('today.completedTodayLabel') }}</span>
              <strong>{{ completedTodayText }}</strong>
            </div>
            <div class="summary-list-item">
              <span>{{ t('today.answerProgress') }}</span>
              <strong>{{ answeredQuestions }} / {{ totalQuestions }}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <article class="stat-card">
        <p class="stat-label">{{ t('today.studyLanguage') }}</p>
        <p class="stat-value">{{ request.language }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.streakDays') }}</p>
        <p class="stat-value">{{ streak?.current_streak ?? 0 }}</p>
        <p class="stat-hint">{{ t('today.bestStreak', { longest: streak?.longest_streak ?? 0 }) }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.completedTodayLabel') }}</p>
        <p class="stat-value">{{ completedTodayText }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.vocabularyCount') }}</p>
        <p class="stat-value">{{ vocabularyCount }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.grammarCount') }}</p>
        <p class="stat-value">{{ grammarCount }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.readingCount') }}</p>
        <p class="stat-value">{{ readingCount }}</p>
      </article>
    </div>

    <div class="section-card" v-if="loading && !lesson">
      <p>{{ t('today.loadingLesson') }}</p>
    </div>

    <div class="section-card" v-else-if="error && !lesson">
      <p class="error-text">{{ error }}</p>
      <button type="button" class="secondary" @click="loadTodayLesson">{{ t('common.retry') }}</button>
    </div>

    <div v-else-if="!lesson && !loading && !error" class="section-card page-stack" data-testid="generate-panel">
      <div class="section-header">
        <div>
          <h2>{{ t('today.generateLesson') }}</h2>
          <p class="section-description">{{ t('today.generateDescription') }}</p>
        </div>
      </div>
      <div class="generate-grid">
        <input v-model="request.topic" :placeholder="t('today.optionalTopic')" data-testid="generate-topic" />
        <select v-model="request.difficulty">
          <option v-for="level in currentLevels" :key="level" :value="level">{{ level }}</option>
        </select>
        <button data-testid="generate-button" :disabled="loadingGenerate" @click="generateLesson">
          {{ loadingGenerate ? t('today.generating') : t('today.generate') }}
        </button>
      </div>
    </div>

    <template v-else>
      <div class="section-card warning-card" v-if="error && lesson">
        <p class="error-text">{{ error }}</p>
      </div>

      <div class="section-card" data-testid="lesson-vocabulary">
        <div class="section-header">
          <div>
            <h2>{{ t('today.vocabulary') }}</h2>
            <p class="section-description">{{ t('today.vocabularyDescription') }}</p>
          </div>
        </div>

        <div class="vocabulary-grid">
          <article
            v-for="(item, idx) in lesson?.vocabulary"
            :key="`${item.word}-${idx}`"
            class="vocabulary-card"
          >
            <div class="vocabulary-card-header">
              <strong>{{ item.word }}</strong>
              <span v-if="item.reading">{{ item.reading }}</span>
              <span v-else-if="item.phonetic">{{ item.phonetic }}</span>
            </div>
            <p class="vocabulary-definition">{{ item.definition_zh }}</p>
            <p class="vocabulary-example">{{ item.example_sentence }}</p>
            <p class="vocabulary-translation">{{ item.example_translation }}</p>
          </article>
        </div>
      </div>

      <div class="section-card" data-testid="lesson-grammar">
        <div class="section-header">
          <div>
            <h2>{{ t('today.grammarExercises') }}</h2>
            <p class="section-description">{{ lesson?.grammar.title }}</p>
          </div>
        </div>

        <div class="grammar-explainer surface-muted">
          <p>{{ lesson?.grammar.explanation }}</p>
        </div>

        <div class="page-stack">
          <article
            v-for="(exercise, index) in lesson?.grammar.exercises"
            :key="`g-${index}`"
            class="question-card"
            :data-testid="`grammar-exercise-${index}`"
          >
            <p class="question-title"><strong>{{ index + 1 }}. {{ exercise.question }}</strong></p>
            <div class="choice-list" v-if="exercise.options?.length">
              <label
                v-for="(option, optionIndex) in exercise.options"
                :key="option"
                class="choice-card"
              >
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
            <input
              v-else
              v-model="answers.grammar[index]"
              :placeholder="t('today.yourAnswer')"
              :data-testid="`grammar-input-${index}`"
            />
          </article>
        </div>
      </div>

      <div class="section-card" data-testid="lesson-reading">
        <div class="section-header">
          <div>
            <h2>{{ t('today.reading') }}</h2>
            <p class="section-description">{{ lesson?.reading.title }}</p>
          </div>
        </div>

        <div class="reading-layout">
          <article class="reading-story surface-muted">
            <h3>{{ t('today.readingArticle') }}</h3>
            <p>{{ lesson?.reading.content }}</p>
          </article>

          <div class="page-stack">
            <article
              v-for="(question, index) in lesson?.reading.questions"
              :key="`r-${index}`"
              class="question-card"
              :data-testid="`reading-question-${index}`"
            >
              <p class="question-title"><strong>{{ index + 1 }}. {{ question.question }}</strong></p>
              <div class="choice-list">
                <label
                  v-for="(option, optionIndex) in question.options"
                  :key="option"
                  class="choice-card"
                >
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
            </article>
          </div>
        </div>
      </div>

      <div class="bottom-action-bar">
        <div>
          <strong>{{ t('today.bottomBarTitle') }}</strong>
          <p>{{ t('today.bottomBarDescription', { answered: answeredQuestions, total: totalQuestions }) }}</p>
        </div>
        <div class="toolbar">
          <button data-testid="submit-review" :disabled="submitting" @click="submitReview">
            {{ submitting ? t('today.submitting') : t('today.submitReview') }}
          </button>
          <button class="secondary" :disabled="!lesson || exportingPdf" @click="exportPdf">
            {{ exportingPdf ? t('today.exportingPdf') : t('today.exportPdf') }}
          </button>
        </div>
      </div>

      <div class="section-card" v-if="reviewResult" data-testid="review-result">
        <div class="section-header">
          <div>
            <h2>{{ t('today.reviewResult') }}</h2>
            <p
              class="section-description"
              data-testid="review-score"
            >
              {{
                t('today.score', {
                  correct: reviewResult.correct_count,
                  total: reviewResult.total_questions,
                  rate: reviewResult.accuracy_rate.toFixed(1),
                })
              }}
            </p>
          </div>
        </div>

        <div class="stats-grid result-stats">
          <article class="stat-card">
            <p class="stat-label">{{ t('today.correctAnswers') }}</p>
            <p class="stat-value">{{ reviewResult.correct_count }}</p>
          </article>
          <article class="stat-card">
            <p class="stat-label">{{ t('today.accuracyRate') }}</p>
            <p class="stat-value">{{ reviewResult.accuracy_rate.toFixed(1) }}%</p>
          </article>
        </div>

        <div v-if="reviewResult.incorrect_items.length" class="page-stack">
          <article v-for="(item, idx) in reviewResult.incorrect_items" :key="idx" class="surface-muted result-card">
            <strong>{{ item.question }}</strong>
            <p>{{ t('today.correctAnswer', { answer: item.correct_answer }) }}</p>
            <p>{{ item.explanation }}</p>
          </article>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { lessonApi, reviewApi, streakApi, systemApi } from '@/services/api'
import type { Language, Lesson, ReviewResult, StreakResponse } from '@/types'
import { buildReviewPayload } from '@/utils/buildReviewPayload'

const { t } = useI18n()

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
const resettingDemo = ref(false)
const exportingPdf = ref(false)

const answers = reactive<{ grammar: Record<number, string>; reading: Record<number, string> }>({
  grammar: {},
  reading: {},
})

const currentLevels = computed(() =>
  request.language === 'EN' ? ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] : ['N5', 'N4', 'N3', 'N2', 'N1'],
)

const vocabularyCount = computed(() => lesson.value?.vocabulary.length ?? 0)
const grammarCount = computed(() => lesson.value?.grammar.exercises.length ?? 0)
const readingCount = computed(() => lesson.value?.reading.questions.length ?? 0)

const totalQuestions = computed(() => grammarCount.value + readingCount.value)

const answeredQuestions = computed(() => {
  if (!lesson.value) return 0
  let count = 0
  for (let i = 0; i < grammarCount.value; i++) {
    const answer = answers.grammar[i]
    if (typeof answer === 'string' && answer.trim().length > 0) count++
  }
  for (let i = 0; i < readingCount.value; i++) {
    const answer = answers.reading[i]
    if (typeof answer === 'string' && answer.trim().length > 0) count++
  }
  return count
})

const completedTodayText = computed(() =>
  streak.value?.today_completed ? t('today.yes') : t('today.no'),
)

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
    console.error(err)
    error.value = t('today.loadError')
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
    console.error(err)
    error.value = t('today.generateError')
  } finally {
    loadingGenerate.value = false
  }
}

const submitReview = async () => {
  if (!lesson.value) return

  const payload = buildReviewPayload(lesson.value, answers)
  if (payload.length === 0) {
    window.alert(t('today.answerAtLeastOne'))
    return
  }

  if (answeredQuestions.value < totalQuestions.value) {
    const ok = window.confirm(
      t('today.unansweredConfirm', {
        answered: answeredQuestions.value,
        total: totalQuestions.value,
      }),
    )
    if (!ok) return
  }

  submitting.value = true
  try {
    reviewResult.value = await reviewApi.submitReview(payload)
    await loadStreak()
  } catch (err) {
    console.error(err)
    error.value = t('today.submitError')
  } finally {
    submitting.value = false
  }
}

const exportPdf = async () => {
  if (!lesson.value || exportingPdf.value) return

  exportingPdf.value = true
  error.value = null
  try {
    await lessonApi.exportPdf(lesson.value.metadata.lesson_id)
  } catch (err) {
    console.error(err)
    error.value = t('today.exportError')
  } finally {
    exportingPdf.value = false
  }
}

const resetDemo = async () => {
  resettingDemo.value = true
  error.value = null
  try {
    await systemApi.resetDemo()
    await Promise.all([loadTodayLesson(), loadStreak()])
  } catch (err) {
    console.error(err)
    error.value = t('today.resetError')
  } finally {
    resettingDemo.value = false
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

<style scoped>
.today-hero {
  display: grid;
  gap: 24px;
}

.today-toolbar {
  min-width: min(100%, 420px);
}

.today-toolbar select {
  min-width: 120px;
}

.today-summary-grid {
  align-items: stretch;
}

.summary-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
}

.summary-card h2 {
  margin: 0 0 8px;
  font-size: 1.1rem;
}

.summary-meta {
  margin: 0;
  color: #64748b;
}

.summary-pills {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.summary-pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-size: 0.9rem;
}

.summary-list {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.summary-list-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #475569;
}

.generate-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) 160px auto;
  gap: 16px;
}

.warning-card {
  border-color: #fecaca;
  background: #fff7f7;
}

.vocabulary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.vocabulary-card {
  padding: 20px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.vocabulary-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.vocabulary-definition,
.vocabulary-example,
.vocabulary-translation {
  margin: 0;
}

.vocabulary-definition {
  color: #0f172a;
  font-weight: 600;
}

.vocabulary-example {
  margin-top: 12px;
  color: #334155;
}

.vocabulary-translation {
  margin-top: 8px;
  color: #64748b;
  font-size: 0.92rem;
}

.grammar-explainer {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  margin-bottom: 20px;
}

.grammar-explainer p {
  margin: 0;
  color: #334155;
}

.question-card {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.question-title {
  margin: 0 0 16px;
}

.choice-list {
  display: grid;
  gap: 12px;
}

.choice-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: #f8fbff;
  cursor: pointer;
}

.choice-card input {
  width: auto;
  margin: 0;
}

.reading-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 24px;
}

.reading-story {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.reading-story h3,
.reading-story p {
  margin: 0;
}

.reading-story p {
  margin-top: 12px;
  white-space: pre-wrap;
}

.bottom-action-bar {
  position: sticky;
  bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 18px 20px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 32px rgba(37, 99, 235, 0.08);
}

.bottom-action-bar p {
  margin: 6px 0 0;
  color: #64748b;
}

.result-stats {
  margin-bottom: 20px;
}

.result-card {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
}

.result-card p {
  margin: 8px 0 0;
}

.error-text {
  color: #b91c1c;
  margin: 0 0 12px;
}

@media (max-width: 900px) {
  .generate-grid,
  .reading-layout {
    grid-template-columns: 1fr;
  }
}
</style>
