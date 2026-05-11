<template>
  <div class="section-card" data-testid="review-result">
    <div class="section-header">
      <div>
        <h2>{{ t('today.reviewResult') }}</h2>
        <p
          class="section-description"
          data-testid="review-score"
        >
          {{
            t('today.score', {
              correct: result.correct_count,
              total: result.total_questions,
              rate: result.accuracy_rate.toFixed(1),
            })
          }}
        </p>
      </div>
    </div>

    <div class="stats-grid result-stats">
      <article class="stat-card">
        <p class="stat-label">{{ t('today.correctAnswers') }}</p>
        <p class="stat-value">{{ result.correct_count }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.accuracyRate') }}</p>
        <p class="stat-value">{{ result.accuracy_rate.toFixed(1) }}%</p>
      </article>
    </div>

    <div v-if="result.incorrect_items.length" class="page-stack">
      <article v-for="(item, idx) in result.incorrect_items" :key="idx" class="surface-muted result-card">
        <strong>{{ item.question }}</strong>
        <p>{{ t('today.correctAnswer', { answer: item.correct_answer }) }}</p>
        <p>{{ item.explanation }}</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ReviewResult } from '@/types'

defineProps<{ result: ReviewResult }>()

const { t } = useI18n()
</script>

<style scoped>
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
</style>
