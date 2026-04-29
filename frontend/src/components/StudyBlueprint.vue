<template>
  <section>
    <div class="row between center">
      <h3>{{ t('studyPlan.title') }}</h3>
      <button class="secondary" @click="plan = null" v-if="plan">{{ t('studyPlan.clear') }}</button>
    </div>

    <div class="grid" style="margin-top: 0.75rem">
      <input v-model="targetGoal" :placeholder="t('studyPlan.placeholder')" />
      <button :disabled="loading || !targetGoal" @click="generatePlan">
        {{ loading ? t('studyPlan.generating') : t('studyPlan.generate') }}
      </button>
    </div>

    <p v-if="error" style="margin-top: 0.75rem; color: #b91c1c">{{ error }}</p>

    <p v-else-if="!plan" style="margin-top: 0.75rem; color: #475569">
      {{ t('studyPlan.empty') }}
    </p>

    <div v-if="plan" style="margin-top: 1rem" class="grid">
      <p>{{ t('studyPlan.dailyCommitment', { minutes: plan.daily_commitment_minutes }) }}</p>
      <p>{{ t('studyPlan.endDate', { date: formatDate(plan.end_date) }) }}</p>
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
import { useI18n } from 'vue-i18n'
import { aiTutorApi } from '@/services/api'
import type { Language, StudyPlan } from '@/types'

const props = defineProps<{ language: Language }>()
const { t } = useI18n()

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
    console.error(err)
    error.value = t('studyPlan.error')
  } finally {
    loading.value = false
  }
}
</script>
