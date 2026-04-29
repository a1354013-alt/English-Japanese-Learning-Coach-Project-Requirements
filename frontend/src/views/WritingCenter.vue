<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div class="panel">
      <h2 v-if="!embedded">{{ t('writing.title') }}</h2>
      <div class="grid">
        <select v-model="submission.language">
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
        <input v-model="submission.topic" :placeholder="t('writing.topicPlaceholder')" />
        <textarea v-model="submission.text" rows="10" :placeholder="t('writing.textPlaceholder')"></textarea>
        <button :disabled="loading || !submission.text.trim()" @click="analyze">{{ loading ? t('writing.analyzing') : t('writing.analyze') }}</button>
      </div>
    </div>

    <div class="panel" v-if="error">
      <p style="color: #b91c1c; margin: 0">{{ error }}</p>
      <button style="margin-top: 0.75rem" class="secondary" :disabled="loading || !submission.text.trim()" @click="analyze">
        {{ t('common.retry') }}
      </button>
    </div>

    <div class="panel" v-else-if="analysis">
      <h3>{{ t('writing.result') }}</h3>
      <p>{{ t('writing.estimatedLevel', { level: analysis.estimated_level }) }}</p>
      <p>{{ t('writing.overallScore', { score: analysis.overall_score }) }}</p>
      <p>{{ analysis.feedback }}</p>
      <h4>{{ t('writing.corrections') }}</h4>
      <ul>
        <li v-for="(item, idx) in analysis.corrections" :key="idx">
          {{ item.original }} -> {{ item.corrected }} ({{ item.type }})
        </li>
      </ul>
      <h4>{{ t('writing.suggestions') }}</h4>
      <ul>
        <li v-for="(item, idx) in analysis.suggestions" :key="idx">{{ item }}</li>
      </ul>
    </div>

    <div class="panel" v-else>
      <p style="margin: 0; color: #475569">{{ t('writing.empty') }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { aiTutorApi } from '@/services/api'
import type { WritingAnalysis, WritingSubmission } from '@/types'

withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
})

const { t } = useI18n()
const loading = ref(false)
const analysis = ref<WritingAnalysis | null>(null)
const error = ref<string | null>(null)

const submission = reactive<WritingSubmission>({
  language: 'EN',
  text: '',
  topic: '',
  target_level: '',
})

const analyze = async () => {
  loading.value = true
  error.value = null
  analysis.value = null
  try {
    const res = await aiTutorApi.analyzeWriting(submission)
    analysis.value = res.analysis
  } catch (err) {
    console.error(err)
    error.value = t('writing.analyzeError')
  } finally {
    loading.value = false
  }
}
</script>
