<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel">
      <h2>{{ t('analytics.title') }}</h2>
      <p style="color: #64748b; margin-bottom: 1.5rem">{{ t('analytics.subtitle') }}</p>

      <div v-if="loading" style="text-align: center; padding: 2rem">{{ t('analytics.loading') }}</div>

      <div v-else-if="error" class="error-panel">
        <p>{{ error }}</p>
        <button @click="loadAnalytics" class="secondary">{{ t('common.retry') }}</button>
      </div>

      <div v-else-if="analytics" class="analytics-grid">
        <div class="stat-card">
          <h3>{{ t('analytics.totalXp') }}</h3>
          <p class="stat-value">{{ analytics.total_xp }}</p>
        </div>
        <div class="stat-card">
          <h3>{{ t('analytics.level') }}</h3>
          <p class="stat-value">{{ analytics.level }}</p>
        </div>
        <div class="stat-card">
          <h3>{{ t('analytics.currentStreak') }}</h3>
          <p class="stat-value">{{ t('analytics.days', { count: analytics.streak }) }}</p>
        </div>
        <div class="stat-card">
          <h3>{{ t('analytics.lessonsCompleted') }}</h3>
          <p class="stat-value">{{ analytics.lessons_completed }}</p>
        </div>

        <div class="panel-section">
          <h3>{{ t('analytics.hardestItems') }}</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">{{ t('analytics.hardestItemsHint') }}</p>
          <ul v-if="analytics.hardest_words.length > 0" class="word-list">
            <li v-for="(word, idx) in analytics.hardest_words" :key="idx" class="word-item">
              <span class="word">{{ word.word }}</span>
              <span class="mistakes">{{ t('analytics.mistakesCount', { count: word.mistakes }) }}</span>
            </li>
          </ul>
          <p v-else style="color: #94a3b8">{{ t('analytics.noWrongAnswers') }}</p>
        </div>

        <div class="panel-section">
          <h3>{{ t('analytics.weakestCategory') }}</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">{{ t('analytics.weakestCategoryHint') }}</p>
          <div v-if="analytics.weakest_category" class="category-badge">
            {{ analytics.weakest_category.category }} ({{ t('analytics.activeItems', { count: analytics.weakest_category.active_items }) }})
          </div>
          <p v-else style="color: #94a3b8">{{ t('analytics.notEnoughData') }}</p>
        </div>

        <div class="panel-section">
          <h3>{{ t('analytics.accuracyTrend') }}</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">{{ t('analytics.accuracyTrendHint') }}</p>
          <div v-if="analytics.accuracy_trend.length > 0" class="trend-grid">
            <div v-for="(p, idx) in analytics.accuracy_trend" :key="idx" class="trend-point">
              <div class="trend-value">{{ Number(p.accuracy_rate).toFixed(1) }}%</div>
              <div class="trend-meta">{{ new Date(p.submitted_at).toLocaleDateString() }}</div>
            </div>
          </div>
          <p v-else style="color: #94a3b8">{{ t('analytics.noReviewHistory') }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { analyticsApi } from '@/services/api'
import type { AnalyticsPayload } from '@/types'

const { t } = useI18n()
const loading = ref(true)
const error = ref<string | null>(null)
const analytics = ref<AnalyticsPayload | null>(null)

const loadAnalytics = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await analyticsApi.getAnalytics()
    analytics.value = res.analytics
  } catch (err) {
    console.error(err)
    error.value = t('analytics.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(loadAnalytics)
</script>

<style scoped>
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

.stat-card h3 {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0 0 0.5rem 0;
  text-transform: uppercase;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #1e293b;
  margin: 0;
}

.panel-section {
  grid-column: span 2;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
}

@media (max-width: 768px) {
  .panel-section {
    grid-column: span 1;
  }
}

.word-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.word-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.word-item:last-child {
  border-bottom: none;
}

.word {
  font-weight: 500;
}

.mistakes {
  color: #ef4444;
  font-size: 0.85rem;
}

.category-badge {
  display: inline-block;
  background: #fef3c7;
  color: #92400e;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
}

.trend-point {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem;
  background: white;
}

.trend-value {
  font-weight: 700;
  font-size: 1.25rem;
}

.trend-meta {
  margin-top: 0.25rem;
  color: #64748b;
  font-size: 0.85rem;
}

.error-panel {
  text-align: center;
  padding: 2rem;
  color: #b91c1c;
}
</style>
