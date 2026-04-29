<template>
  <section class="page-shell page-stack">
    <div class="hero-card">
      <div class="page-header">
        <div>
          <span class="page-eyebrow">{{ t('progressCenter.eyebrow') }}</span>
          <h1 class="page-title">{{ t('progressCenter.title') }}</h1>
          <p class="page-subtitle">{{ t('progressCenter.subtitle') }}</p>
        </div>
      </div>

      <div class="tab-list">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="tab-button"
          :class="{ active: currentTab === tab.key }"
          @click="setTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="section-card">{{ t('progress.loading') }}</div>

    <div v-else-if="error" class="section-card">
      <p class="error-text">{{ error }}</p>
      <button type="button" @click="loadProgress">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="progress">
      <div v-if="currentTab === 'overview'" class="page-stack">
        <div class="stats-grid">
          <article class="stat-card">
            <p class="stat-label">{{ t('progressCenter.rpgLevel') }}</p>
            <p class="stat-value">{{ progress.rpg_stats.level }}</p>
            <p class="stat-hint">{{ progress.rpg_stats.title }}</p>
          </article>
          <article class="stat-card">
            <p class="stat-label">{{ t('progressCenter.totalXp') }}</p>
            <p class="stat-value">{{ progress.rpg_stats.total_xp }}</p>
            <p class="stat-hint">
              {{ t('progressCenter.currentXp', { current: progress.rpg_stats.current_xp, next: progress.rpg_stats.next_level_xp }) }}
            </p>
          </article>
          <article class="stat-card">
            <p class="stat-label">{{ t('progressCenter.streakDays') }}</p>
            <p class="stat-value">{{ progress.rpg_stats.streak_days }}</p>
            <p class="stat-hint">{{ t('progressCenter.updatedAt', { time: formatDateTime(progress.updated_at) }) }}</p>
          </article>
          <article class="stat-card">
            <p class="stat-label">{{ t('progressCenter.wordCardsCount') }}</p>
            <p class="stat-value">{{ progress.rpg_stats.word_cards.length }}</p>
            <p class="stat-hint">{{ t('progressCenter.unlockedSkills', { count: progress.rpg_stats.unlocked_skills.length }) }}</p>
          </article>
        </div>

        <div class="section-card">
          <div class="section-header">
            <div>
              <h2>{{ t('progressCenter.languageProgress') }}</h2>
              <p class="section-description">{{ t('progressCenter.languageProgressDescription') }}</p>
            </div>
          </div>

          <div class="language-progress-grid">
            <article class="progress-language-card">
              <h3>{{ t('progress.titleEnglish') }}</h3>
              <p>{{ t('progress.currentLevel', { level: progress.english_progress.current_level }) }}</p>
              <p>
                {{ t('progress.completedLessons', { count: progress.english_progress.completed_lessons }) }}
                <span data-testid="progress-en-completed" style="display: none">{{ progress.english_progress.completed_lessons }}</span>
              </p>
              <p>{{ t('progress.accuracy', { rate: progress.english_progress.accuracy_rate.toFixed(1) }) }}</p>
            </article>
            <article class="progress-language-card">
              <h3>{{ t('progress.titleJapanese') }}</h3>
              <p>{{ t('progress.currentLevel', { level: progress.japanese_progress.current_level }) }}</p>
              <p>{{ t('progress.completedLessons', { count: progress.japanese_progress.completed_lessons }) }}</p>
              <p>{{ t('progress.accuracy', { rate: progress.japanese_progress.accuracy_rate.toFixed(1) }) }}</p>
            </article>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <div>
              <h2>{{ t('progress.collectedWordCards') }}</h2>
              <p class="section-description">{{ t('progressCenter.wordCardsDescription') }}</p>
            </div>
          </div>

          <div v-if="progress.rpg_stats.word_cards.length > 0" class="word-card-grid">
            <article
              v-for="card in progress.rpg_stats.word_cards"
              :key="`${card.language}-${card.word}`"
              class="word-card-surface"
            >
              <div class="word-card-topline">
                <strong>{{ card.word }}</strong>
                <span>{{ card.rarity }}</span>
              </div>
              <p>{{ card.definition_zh || t('progressCenter.noDefinition') }}</p>
              <small>{{ card.example_sentence || '' }}</small>
            </article>
          </div>
          <p v-else>{{ t('progress.noCards') }}</p>
        </div>

        <div class="section-card">
          <StudyBlueprint :language="preferredLanguage" />
        </div>
      </div>

      <div v-else-if="currentTab === 'mistakes'" class="section-card">
        <div class="section-header">
          <div>
            <h2>{{ t('progressCenter.tabs.mistakes') }}</h2>
            <p class="section-description">{{ t('progressCenter.tabDescriptions.mistakes') }}</p>
          </div>
        </div>
        <WrongAnswers embedded />
      </div>

      <div v-else-if="currentTab === 'review'" class="section-card">
        <div class="section-header">
          <div>
            <h2>{{ t('progressCenter.tabs.review') }}</h2>
            <p class="section-description">{{ t('progressCenter.tabDescriptions.review') }}</p>
          </div>
        </div>
        <SrsReview embedded />
      </div>

      <div v-else class="section-card">
        <div class="section-header">
          <div>
            <h2>{{ t('progressCenter.tabs.history') }}</h2>
            <p class="section-description">{{ t('progressCenter.tabDescriptions.history') }}</p>
          </div>
        </div>
        <Archive embedded />
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import StudyBlueprint from '@/components/StudyBlueprint.vue'
import { progressApi } from '@/services/api'
import type { Language, UserProgress } from '@/types'
import Archive from '@/views/Archive.vue'
import SrsReview from '@/views/SrsReview.vue'
import WrongAnswers from '@/views/WrongAnswers.vue'

type ProgressTab = 'overview' | 'mistakes' | 'review' | 'history'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const progress = ref<UserProgress | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const tabs = computed(() => [
  { key: 'overview' as const, label: t('progressCenter.tabs.overview') },
  { key: 'mistakes' as const, label: t('progressCenter.tabs.mistakes') },
  { key: 'review' as const, label: t('progressCenter.tabs.review') },
  { key: 'history' as const, label: t('progressCenter.tabs.history') },
])

const currentTab = computed<ProgressTab>(() => {
  const tab = route.query.tab
  if (tab === 'mistakes' || tab === 'review' || tab === 'history' || tab === 'overview') {
    return tab
  }
  return 'overview'
})

const preferredLanguage = computed<Language>(() => {
  if (!progress.value) return 'EN'
  return progress.value.english_progress.accuracy_rate >= progress.value.japanese_progress.accuracy_rate ? 'EN' : 'JP'
})

const formatDateTime = (value: string) => new Date(value).toLocaleString()

const setTab = (tab: ProgressTab) => {
  void router.replace({ path: '/progress', query: { tab } })
}

const loadProgress = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await progressApi.getProgress()
    progress.value = response.progress
  } catch (err) {
    console.error(err)
    error.value = t('progress.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(loadProgress)
</script>

<style scoped>
.language-progress-grid,
.word-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.progress-language-card,
.word-card-surface {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.progress-language-card h3,
.progress-language-card p,
.word-card-surface p,
.word-card-surface small {
  margin: 0;
}

.progress-language-card p + p,
.word-card-surface p,
.word-card-surface small {
  margin-top: 10px;
}

.word-card-topline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.word-card-topline span {
  color: #1d4ed8;
  font-weight: 700;
}

.error-text {
  color: #b91c1c;
  margin: 0 0 12px;
}
</style>
