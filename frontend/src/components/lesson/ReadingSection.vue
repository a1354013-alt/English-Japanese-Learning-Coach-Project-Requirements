<template>
  <div class="section-card" data-testid="lesson-reading">
    <div class="section-header">
      <div>
        <h2>{{ t('today.reading') }}</h2>
        <p class="section-description">{{ reading.title }}</p>
      </div>
    </div>

    <div class="reading-layout">
      <article class="reading-story surface-muted">
        <h3>{{ t('today.readingArticle') }}</h3>
        <p>{{ reading.content }}</p>
      </article>

      <div class="page-stack">
        <article
          v-for="(question, index) in reading.questions"
          :key="`r-${index}`"
          class="question-card"
          :data-testid="`reading-question-${index}`"
        >
          <p class="question-title">
            <strong>{{ index + 1 }}. {{ question.question }}</strong>
          </p>
          <div class="choice-list">
            <label
              v-for="(option, optionIndex) in question.options"
              :key="option"
              class="choice-card"
            >
              <input
                type="radio"
                :name="`r-${index}`"
                :value="option"
                :checked="answers[index] === option"
                :data-testid="`reading-option-${index}-${optionIndex}`"
                @change="$emit('update-answer', index, option)"
              />
              <span>{{ option }}</span>
            </label>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ReadingSection } from '@/types'

defineProps<{
  reading: ReadingSection
  answers: Record<number, string>
}>()

defineEmits<{
  'update-answer': [index: number, value: string]
}>()

const { t } = useI18n()
</script>

<style scoped>
.question-card {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.question-title {
  margin: 0 0 16px;
}

.choice-list {
  display: grid;
  gap: 12px;
}

.choice-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: #f8fbff;
  cursor: pointer;
}

.choice-card input {
  width: auto;
  margin: 0;
}

.reading-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 24px;
}

.reading-story {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.reading-story h3,
.reading-story p {
  margin: 0;
}

.reading-story p {
  margin-top: 12px;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .reading-layout {
    grid-template-columns: 1fr;
  }
}
</style>
