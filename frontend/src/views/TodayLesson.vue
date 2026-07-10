<template>
  <section class="page-shell page-stack" data-testid="today-lesson">
    <DiagnosticFlow
      v-if="microLoaded && !microDiagnosticCompleted"
      @complete="handleDiagnosticComplete"
    />

    <LessonHeader
      v-if="!microLoaded || microDiagnosticCompleted"
      :lesson="lesson"
      :language="request.language"
      :streak="streak"
      :completed-today-text="completedTodayText"
      :answered-questions="answeredQuestions"
      :total-questions="totalQuestions"
      :vocabulary-count="vocabularyCount"
      :grammar-count="grammarCount"
      :reading-count="readingCount"
      :resetting-demo="resettingDemo"
      @update:language="request.language = $event"
      @refresh="loadTodayLesson"
      @reset-demo="resetDemo"
    />

    <TodayMissionPanel v-if="studyMission" :mission="studyMission" />

    <LoadingState
      v-if="(loading && !lesson) || microLoading"
      :message="t('today.loadingLesson')"
    />

    <ErrorState
      v-else-if="error && !lesson"
      :message="error"
      :retry-label="t('common.retry')"
      @retry="loadTodayLesson"
    />

    <MicroLesson
      v-if="microLesson && microDiagnosticCompleted"
      :lesson="microLesson"
      :plan="learningPlan"
      @completed="handleMicroCompleted"
    />

    <div
      v-if="microDiagnosticCompleted && !lesson && !loading && !error"
      class="section-card page-stack"
      data-testid="generate-panel"
    >
      <div class="section-header">
        <div>
          <h2>{{ t('today.generateLesson') }}</h2>
          <p class="section-description">
            {{ t('today.generateDescription') }}
          </p>
        </div>
      </div>
      <div class="generate-grid">
        <input
          v-model="request.topic"
          :placeholder="t('today.optionalTopic')"
          data-testid="generate-topic"
        />
        <select v-model="request.difficulty">
          <option v-for="level in currentLevels" :key="level" :value="level">
            {{ level }}
          </option>
        </select>
        <button
          data-testid="generate-button"
          :disabled="loadingGenerate"
          @click="generateLesson"
        >
          {{ loadingGenerate ? t('today.generating') : t('today.generate') }}
        </button>
      </div>
    </div>

    <template v-if="microDiagnosticCompleted && lesson">
      <div v-if="error && lesson" class="section-card warning-card">
        <p class="error-text">{{ error }}</p>
      </div>

      <div
        v-if="lesson.objectives?.length"
        class="section-card"
        data-testid="lesson-objectives"
      >
        <div class="section-header">
          <div>
            <h2>{{ t('lessonSections.objectives.title') }}</h2>
            <p class="section-description">
              {{ t('lessonSections.objectives.description') }}
            </p>
          </div>
        </div>
        <ol>
          <li v-for="objective in lesson.objectives" :key="objective">
            {{ objective }}
          </li>
        </ol>
      </div>
      <VocabularySection :vocabulary="lesson.vocabulary" />
      <WordRootsSection :word-roots="lesson.word_roots ?? []" />
      <SentencePatternSection
        :sentence-patterns="lesson.sentence_patterns ?? []"
      />
      <GrammarSection
        :grammar="lesson.grammar"
        :answers="answers.grammar"
        @update-answer="setGrammarAnswer"
      />
      <DialogueSection :dialogue="lesson.dialogue" />
      <ReadingSection
        :reading="lesson.reading"
        :answers="answers.reading"
        @update-answer="setReadingAnswer"
      />
      <ImmersionSection
        :immersion="lesson.immersion"
        :tts-available="ttsAvailability.available"
        :tts-message="ttsAvailability.message"
      />
      <LessonActions
        :answered-questions="answeredQuestions"
        :total-questions="totalQuestions"
        :submitting="submitting"
        :exporting-pdf="exportingPdf"
        :export-disabled="!lesson"
        @submit-review="submitReview"
        @export-pdf="exportPdf"
      />
      <ReviewPanel v-if="reviewResult" :result="reviewResult" />
      <FeynmanSection
        :feynman="lesson.feynman_prompt"
        :lesson-id="lesson.metadata.lesson_id"
        :language="lesson.metadata.language"
        :lesson-snapshot="lesson"
      />
      <ReviewPlanSection :review-plan="lesson.review_plan" />
    </template>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DiagnosticFlow from '@/components/DiagnosticFlow.vue'
import MicroLesson from '@/components/MicroLesson.vue'
import TodayMissionPanel from '@/components/TodayMissionPanel.vue'
import ErrorState from '@/components/state/ErrorState.vue'
import LoadingState from '@/components/state/LoadingState.vue'
import DialogueSection from '@/components/lesson/DialogueSection.vue'
import FeynmanSection from '@/components/lesson/FeynmanSection.vue'
import GrammarSection from '@/components/lesson/GrammarSection.vue'
import ImmersionSection from '@/components/lesson/ImmersionSection.vue'
import LessonActions from '@/components/lesson/LessonActions.vue'
import LessonHeader from '@/components/lesson/LessonHeader.vue'
import ReadingSection from '@/components/lesson/ReadingSection.vue'
import ReviewPanel from '@/components/lesson/ReviewPanel.vue'
import ReviewPlanSection from '@/components/lesson/ReviewPlanSection.vue'
import SentencePatternSection from '@/components/lesson/SentencePatternSection.vue'
import VocabularySection from '@/components/lesson/VocabularySection.vue'
import WordRootsSection from '@/components/lesson/WordRootsSection.vue'
import {
  lessonApi,
  microLessonApi,
  reviewApi,
  studyApi,
  streakApi,
  systemApi,
} from '@/services/api'
import { requestConfirmation, showNotice } from '@/services/appFeedback'
import type {
  Language,
  LearningLevel,
  Lesson,
  LearningPlan,
  MicroLesson as MicroLessonType,
  ReviewResult,
  StreakResponse,
  DailyStudyMission,
} from '@/types'
import { formatApiErrorDetail } from '@/utils/apiErrorDetail'
import { buildReviewPayload } from '@/utils/buildReviewPayload'

const { t } = useI18n()

const request = reactive<{
  language: Language
  topic: string
  difficulty: LearningLevel
}>({
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
const microLesson = ref<MicroLessonType | null>(null)
const learningPlan = ref<LearningPlan | null>(null)
const microDiagnosticCompleted = ref(true)
const microLoaded = ref(false)
const microLoading = ref(false)
const studyMission = ref<DailyStudyMission | null>(null)
const ttsAvailability = reactive<{
  available: boolean
  message: string | null
}>({
  available: false,
  message: null,
})

const answers = reactive<{
  grammar: Record<number, string>
  reading: Record<number, string>
}>({
  grammar: {},
  reading: {},
})

const currentLevels = computed(() =>
  request.language === 'EN'
    ? ['A1', 'A2', 'B1', 'B2', 'C1']
    : ['N5', 'N4', 'N3', 'N2', 'N1'],
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

const firstTtsProbeText = (currentLesson: Lesson) =>
  currentLesson.immersion?.shadowing_text?.[0]?.text ||
  currentLesson.dialogue?.dialogue?.[0]?.text ||
  currentLesson.reading?.content ||
  currentLesson.metadata.topic

const refreshTtsAvailability = async (currentLesson: Lesson | null) => {
  ttsAvailability.available = false
  ttsAvailability.message = null
  if (!currentLesson) return

  try {
    const response = await lessonApi.getTts(
      firstTtsProbeText(currentLesson),
      currentLesson.metadata.language,
    )
    ttsAvailability.available = response.available && response.mode === 'live'
    ttsAvailability.message = response.available
      ? null
      : response.message || t('lessonSections.immersion.ttsUnavailable')
  } catch {
    ttsAvailability.message = t('lessonSections.immersion.ttsUnavailable')
  }
}

const setGrammarAnswer = (index: number, value: string) => {
  answers.grammar[index] = value
}

const setReadingAnswer = (index: number, value: string) => {
  answers.reading[index] = value
}

const loadTodayLesson = async () => {
  loading.value = true
  error.value = null
  try {
    await Promise.all([loadMicroLesson(), loadStudyMission()])
    const res = await lessonApi.getTodayLesson(request.language)
    lesson.value = res.lesson
    resetAnswers()
    await refreshTtsAvailability(lesson.value)
  } catch (err) {
    console.error(err)
    error.value = t('today.loadError')
  } finally {
    loading.value = false
  }
}

const loadStudyMission = async () => {
  try {
    const res = await studyApi.getTodayMission()
    studyMission.value = res.mission
  } catch (err) {
    console.error(err)
    studyMission.value = null
  }
}

const loadMicroLesson = async () => {
  microLoading.value = true
  try {
    const res = await microLessonApi.getToday()
    microDiagnosticCompleted.value = res.diagnostic_completed
    learningPlan.value = res.learning_plan
    microLesson.value = res.lesson
  } finally {
    microLoaded.value = true
    microLoading.value = false
  }
}

const handleDiagnosticComplete = async (plan: LearningPlan) => {
  learningPlan.value = plan
  microDiagnosticCompleted.value = true
  await Promise.all([loadMicroLesson(), loadStudyMission()])
}

const handleMicroCompleted = async (nextLesson: MicroLessonType) => {
  microLesson.value = nextLesson
  await Promise.all([loadStreak(), loadStudyMission()])
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
    await refreshTtsAvailability(lesson.value)
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
    showNotice(t('today.answerAtLeastOne'), 'warning')
    return
  }

  if (answeredQuestions.value < totalQuestions.value) {
    showNotice(
      t('today.reviewIncomplete', {
        answered: answeredQuestions.value,
        total: totalQuestions.value,
      }),
      'warning',
    )
    return
  }

  submitting.value = true
  try {
    reviewResult.value = await reviewApi.submitReview(payload)
    await Promise.all([loadStreak(), loadStudyMission()])
  } catch (err) {
    console.error(err)
    error.value = axios.isAxiosError(err)
      ? formatApiErrorDetail(err.response?.data)
      : t('today.submitError')
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
  const confirmed = await requestConfirmation({
    title: t('today.resetDemoConfirmTitle'),
    message: t('today.resetDemoConfirmMessage'),
    confirmLabel: t('today.resetDemo'),
    cancelLabel: t('common.cancel'),
  })
  if (!confirmed) return

  resettingDemo.value = true
  error.value = null
  try {
    await systemApi.resetDemo()
    await Promise.all([loadTodayLesson(), loadStreak(), loadStudyMission()])
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
.generate-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) 160px auto;
  gap: 16px;
}

.warning-card {
  border-color: #fecaca;
  background: #fff7f7;
}

.error-text {
  color: #b91c1c;
  margin: 0 0 12px;
}

@media (max-width: 900px) {
  .generate-grid {
    grid-template-columns: 1fr;
  }
}
</style>
