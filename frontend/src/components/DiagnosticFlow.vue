<template>
  <section class="section-card page-stack" data-testid="diagnostic-flow">
    <div class="section-header">
      <div>
        <h2>{{ t('microLesson.diagnosticTitle') }}</h2>
        <p class="section-description">
          {{ t('microLesson.diagnosticDescription') }}
        </p>
      </div>
    </div>

    <LoadingState v-if="loading" :message="t('common.loading')" />
    <ErrorState
      v-else-if="error"
      :message="error"
      :retry-label="t('common.retry')"
      @retry="loadQuestions"
    />

    <form v-else class="diagnostic-form" @submit.prevent="submitDiagnostic">
      <fieldset
        v-for="question in questions"
        :key="question.question_id"
        class="diagnostic-question"
      >
        <legend>{{ question.prompt }}</legend>
        <label
          v-for="choice in question.choices"
          :key="choice"
          class="choice-row"
        >
          <input
            v-model="answers[question.question_id]"
            type="radio"
            :name="question.question_id"
            :value="choice"
          />
          <span>{{ choice }}</span>
        </label>
      </fieldset>

      <button type="submit" :disabled="submitting || !canSubmit">
        {{
          submitting
            ? t('microLesson.submittingDiagnostic')
            : t('common.submit')
        }}
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import ErrorState from '@/components/state/ErrorState.vue'
import LoadingState from '@/components/state/LoadingState.vue'
import { diagnosticApi } from '@/services/api'
import type { DiagnosticQuestion, LearningPlan } from '@/types'

const emit = defineEmits<{
  complete: [plan: LearningPlan]
}>()

const { t } = useI18n()
const questions = ref<DiagnosticQuestion[]>([])
const answers = reactive<Record<string, string>>({})
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)

const canSubmit = computed(
  () =>
    questions.value.length > 0 &&
    questions.value.every((question) => Boolean(answers[question.question_id])),
)

const loadQuestions = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await diagnosticApi.getQuestions()
    questions.value = response.questions
  } catch (err) {
    console.error(err)
    error.value = t('microLesson.diagnosticLoadError')
  } finally {
    loading.value = false
  }
}

const submitDiagnostic = async () => {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = null
  try {
    const response = await diagnosticApi.submit(
      questions.value.map((question) => ({
        question_id: question.question_id,
        answer: answers[question.question_id],
      })),
    )
    emit('complete', response.learning_plan)
  } catch (err) {
    console.error(err)
    error.value = t('microLesson.diagnosticSubmitError')
  } finally {
    submitting.value = false
  }
}

onMounted(loadQuestions)
</script>

<style scoped>
.diagnostic-form,
.diagnostic-question {
  display: grid;
  gap: 12px;
}

.diagnostic-question {
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 16px;
}

.diagnostic-question legend {
  font-weight: 700;
  padding: 0 6px;
}

.choice-row {
  align-items: center;
  display: flex;
  gap: 10px;
}
</style>
