<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel">
      <h2>Writing Center</h2>
      <div class="grid">
        <select v-model="submission.language">
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
        <input v-model="submission.topic" placeholder="Optional topic" />
        <textarea v-model="submission.text" rows="10" placeholder="Enter your writing"></textarea>
        <button :disabled="loading || !submission.text.trim()" @click="analyze">{{ loading ? 'Analyzing...' : 'Analyze' }}</button>
      </div>
    </div>

    <div class="panel" v-if="error">
      <p style="color: #b91c1c; margin: 0">{{ error }}</p>
    </div>

    <div class="panel" v-if="analysis">
      <h3>Result</h3>
      <p>Estimated level: {{ analysis.estimated_level }}</p>
      <p>Overall score: {{ analysis.overall_score }}</p>
      <p>{{ analysis.feedback }}</p>
      <h4>Corrections</h4>
      <ul>
        <li v-for="(item, idx) in analysis.corrections" :key="idx">
          {{ item.original }} -> {{ item.corrected }} ({{ item.type }})
        </li>
      </ul>
      <h4>Suggestions</h4>
      <ul>
        <li v-for="(item, idx) in analysis.suggestions" :key="idx">{{ item }}</li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { aiTutorApi } from '@/services/api'
import type { WritingAnalysis, WritingSubmission } from '@/types'

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
  } catch {
    error.value = 'Failed to analyze writing. Check that the API is running and try again.'
  } finally {
    loading.value = false
  }
}
</script>
