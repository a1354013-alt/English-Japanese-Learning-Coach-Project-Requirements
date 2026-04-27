<template>
  <section>
    <div class="row between center">
      <h3>Study Plan</h3>
      <button class="secondary" @click="plan = null" v-if="plan">Clear</button>
    </div>

    <div class="grid" style="margin-top: 0.75rem">
      <input v-model="targetGoal" placeholder="Target goal, e.g. TOEIC 800" />
      <button :disabled="loading || !targetGoal" @click="generatePlan">{{ loading ? 'Generating...' : 'Generate Plan' }}</button>
    </div>

    <p v-if="error" style="margin-top: 0.75rem; color: #b91c1c">{{ error }}</p>

    <p v-else-if="!plan" style="margin-top: 0.75rem; color: #475569">
      No study plan yet. Generate one to show a structured roadmap in the demo.
    </p>

    <div v-if="plan" style="margin-top: 1rem" class="grid">
      <p>Daily commitment: {{ plan.daily_commitment_minutes }} minutes</p>
      <p>End date: {{ formatDate(plan.end_date) }}</p>
      <ul>
        <li v-for="(milestone, idx) in plan.milestones" :key="idx">
          {{ milestone.title }} - {{ formatDate(milestone.target_date) }}
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { aiTutorApi } from '@/services/api'
import type { Language, StudyPlan } from '@/types'

const props = defineProps<{ language: Language }>()

const loading = ref(false)
const targetGoal = ref('')
const plan = ref<StudyPlan | null>(null)
const error = ref<string | null>(null)

const formatDate = (date: string): string => new Date(date).toLocaleDateString()

const generatePlan = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await aiTutorApi.generateStudyPlan(targetGoal.value, props.language)
    if (response.success) {
      plan.value = response.plan
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to generate study plan'
  } finally {
    loading.value = false
  }
}
</script>
