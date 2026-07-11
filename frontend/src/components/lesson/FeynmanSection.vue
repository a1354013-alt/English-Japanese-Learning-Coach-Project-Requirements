<template>
  <div v-if="hasContent" class="section-card" data-testid="lesson-feynman">
    <div class="section-header">
      <div>
        <h2>{{ t('lessonSections.feynman.title') }}</h2>
        <p v-if="safeFeynman.prompt" class="section-description">
          {{ safeFeynman.prompt }}
        </p>
      </div>
    </div>
    <ul v-if="safeFeynman.checklist.length">
      <li v-for="item in safeFeynman.checklist" :key="item">{{ item }}</li>
    </ul>
    <textarea
      v-model="draft"
      rows="5"
      :placeholder="t('lessonSections.feynman.placeholder')"
      data-testid="feynman-input"
    />
    <div class="row gap-sm" style="margin-top: 12px">
      <button
        :disabled="submitting || draft.trim().length === 0"
        data-testid="feynman-submit"
        @click="submit"
      >
        {{
          submitting
            ? t('lessonSections.feynman.submitting')
            : t('lessonSections.feynman.submit')
        }}
      </button>
    </div>
    <p v-if="error" class="feedback-error" data-testid="feynman-error">
      {{ error }}
    </p>
    <div
      v-if="feedback"
      class="feedback-card"
      data-testid="feynman-feedback"
      style="margin-top: 16px"
    >
      <p class="feedback-score">
        {{ t('lessonSections.feynman.score', { score: feedback.score }) }}
      </p>
      <p>{{ feedback.summary }}</p>
      <div v-if="feedback.strengths.length">
        <strong>{{ t('lessonSections.feynman.strengths') }}</strong>
        <ul>
          <li v-for="item in feedback.strengths" :key="`s-${item}`">
            {{ item }}
          </li>
        </ul>
      </div>
      <div v-if="feedback.missing_points.length">
        <strong>{{ t('lessonSections.feynman.missingPoints') }}</strong>
        <ul>
          <li v-for="item in feedback.missing_points" :key="`m-${item}`">
            {{ item }}
          </li>
        </ul>
      </div>
      <div v-if="feedback.corrections.length">
        <strong>{{ t('lessonSections.feynman.corrections') }}</strong>
        <ul>
          <li v-for="item in feedback.corrections" :key="`c-${item}`">
            {{ item }}
          </li>
        </ul>
      </div>
      <div>
        <strong>{{ t('lessonSections.feynman.simpleExplanation') }}</strong>
        <p>{{ feedback.suggested_simple_explanation }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { lessonApi } from '@/services/api'
import type { FeynmanFeedback, FeynmanPrompt, Language } from '@/types'
import { formatApiErrorDetail } from '@/utils/apiErrorDetail'

const props = defineProps<{
  feynman?: FeynmanPrompt
  lessonId: string
  language: Language
}>()
const { t } = useI18n()

const draft = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)
const feedback = ref<FeynmanFeedback | null>(null)

const safeFeynman = computed<FeynmanPrompt>(() => ({
  prompt: props.feynman?.prompt ?? '',
  checklist: props.feynman?.checklist ?? [],
}))
const hasContent = computed(
  () =>
    safeFeynman.value.prompt.length > 0 ||
    safeFeynman.value.checklist.length > 0,
)

const submit = async () => {
  if (!props.lessonId || draft.value.trim().length === 0) return
  submitting.value = true
  error.value = null
  try {
    const response = await lessonApi.submitFeynmanFeedback(props.lessonId, {
      explanation: draft.value.trim(),
      language: props.language,
    })
    feedback.value = response.feedback
  } catch (err) {
    feedback.value = null
    error.value = axios.isAxiosError(err)
      ? formatApiErrorDetail(err.response?.data)
      : t('lessonSections.feynman.error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.feedback-card {
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
}

.feedback-score {
  font-weight: 700;
}

.feedback-error {
  color: #b91c1c;
  margin-top: 12px;
}
</style>
