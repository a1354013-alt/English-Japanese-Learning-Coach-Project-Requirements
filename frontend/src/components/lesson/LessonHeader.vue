<template>
  <div class="page-stack">
    <div class="hero-card today-hero">
      <div class="page-header">
        <div>
          <span class="page-eyebrow">{{ t('today.eyebrow') }}</span>
          <h1 class="page-title" data-testid="today-lesson-title">
            {{ t('today.title') }}
          </h1>
          <p class="page-subtitle">
            {{ lesson?.metadata.topic || t('today.noLesson') }}
          </p>
        </div>

        <div class="toolbar today-toolbar">
          <select
            :value="language"
            :aria-label="t('common.language')"
            @change="emitLanguage"
          >
            <option value="EN">{{ t('common.english') }}</option>
            <option value="JP">{{ t('common.japanese') }}</option>
          </select>
          <button
            type="button"
            class="secondary"
            :disabled="resettingDemo"
            @click="$emit('reset-demo')"
          >
            {{
              resettingDemo ? t('today.resettingDemo') : t('today.resetDemo')
            }}
          </button>
          <button type="button" class="secondary" @click="$emit('refresh')">
            {{ t('common.refresh') }}
          </button>
        </div>
      </div>

      <div v-if="lesson" class="content-grid-2 today-summary-grid">
        <div class="surface-muted summary-card">
          <h2>{{ t('today.summaryTitle') }}</h2>
          <p class="summary-meta">
            {{ lesson.metadata.language }} / {{ lesson.metadata.level }} /
            {{
              t('today.estimatedDuration', {
                minutes: lesson.metadata.estimated_duration_minutes,
              })
            }}
          </p>
          <div class="summary-pills">
            <span
              v-for="(point, index) in lesson.metadata.key_points"
              :key="`${point}-${index}`"
              class="summary-pill"
            >
              {{ point }}
            </span>
          </div>
        </div>

        <div class="surface-muted summary-card">
          <h2>{{ t('today.todayStatus') }}</h2>
          <div class="summary-list">
            <div class="summary-list-item">
              <span>{{ t('today.studyLanguage') }}</span>
              <strong>{{ language }}</strong>
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
        <p class="stat-value">{{ language }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ t('today.streakDays') }}</p>
        <p class="stat-value">{{ streak?.current_streak ?? 0 }}</p>
        <p class="stat-hint">
          {{ t('today.bestStreak', { longest: streak?.longest_streak ?? 0 }) }}
        </p>
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
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Language, Lesson, StreakResponse } from '@/types'

defineProps<{
  lesson: Lesson | null
  language: Language
  streak: StreakResponse | null
  completedTodayText: string
  answeredQuestions: number
  totalQuestions: number
  vocabularyCount: number
  grammarCount: number
  readingCount: number
  resettingDemo: boolean
}>()

const emit = defineEmits<{
  'update:language': [value: Language]
  refresh: []
  'reset-demo': []
}>()

const { t } = useI18n()

const emitLanguage = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  if (value === 'EN' || value === 'JP') {
    emit('update:language', value)
  }
}
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
</style>
