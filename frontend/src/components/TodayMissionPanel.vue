<template>
  <section class="mission-panel" data-testid="today-mission-panel">
    <div class="mission-main">
      <p class="eyebrow">{{ t('todayMission.eyebrow') }}</p>
      <h2>{{ mission.today_goal_text }}</h2>
      <p>{{ mission.completion_summary.text }}</p>
    </div>

    <div class="mission-grid">
      <div class="mission-metric">
        <span>{{ t('todayMission.microStatus') }}</span>
        <strong>{{
          t(`todayMission.micro.${mission.micro_lesson_status}`)
        }}</strong>
      </div>
      <div class="mission-metric">
        <span>{{ t('todayMission.dueSrs') }}</span>
        <strong>{{ mission.due_counts.total }}</strong>
      </div>
      <div class="mission-metric">
        <span>{{ t('todayMission.weakVocabulary') }}</span>
        <strong>{{ mission.weak_counts.vocabulary }}</strong>
      </div>
      <div class="mission-metric">
        <span>{{ t('todayMission.weakGrammar') }}</span>
        <strong>{{ mission.weak_counts.grammar }}</strong>
      </div>
      <div class="mission-metric">
        <span>{{ t('todayMission.weakSentencePatterns') }}</span>
        <strong>{{ mission.weak_counts.sentence_pattern }}</strong>
      </div>
    </div>

    <div class="mission-next">
      <span>{{ t('todayMission.suggestedNext') }}</span>
      <strong>
        {{ mission.suggested_next_lesson.language }}
        {{ mission.suggested_next_lesson.level }}
      </strong>
      <p>{{ mission.suggested_next_lesson.topic }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { DailyStudyMission } from '@/types'

defineProps<{
  mission: DailyStudyMission
}>()

const { t } = useI18n()
</script>

<style scoped>
.mission-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 1.7fr);
  gap: 18px;
  padding: 22px;
  border: 1px solid #d8e2ea;
  border-radius: 8px;
  background: #fbfdff;
  box-shadow: 0 8px 22px rgb(15 23 42 / 0.06);
}

.mission-main h2,
.mission-main p,
.mission-next p {
  margin: 0;
}

.mission-main {
  display: grid;
  gap: 8px;
}

.eyebrow,
.mission-metric span,
.mission-next span {
  margin: 0;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.mission-main h2 {
  color: #0f172a;
  font-size: 1.35rem;
  line-height: 1.25;
}

.mission-main p,
.mission-next p {
  color: #475569;
}

.mission-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(92px, 1fr));
  gap: 10px;
}

.mission-metric,
.mission-next {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.mission-metric {
  display: grid;
  gap: 6px;
  min-height: 82px;
}

.mission-metric strong {
  color: #0f766e;
  font-size: 1.35rem;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.mission-next {
  grid-column: 2 / 3;
}

.mission-next strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
}

@media (max-width: 980px) {
  .mission-panel {
    grid-template-columns: 1fr;
  }

  .mission-grid,
  .mission-next {
    grid-column: auto;
  }
}

@media (max-width: 720px) {
  .mission-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
