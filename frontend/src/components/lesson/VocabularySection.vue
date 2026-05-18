<template>
  <div class="section-card" data-testid="lesson-vocabulary">
    <div class="section-header">
      <div>
        <h2>{{ t('today.vocabulary') }}</h2>
        <p class="section-description">
          {{ t('today.vocabularyDescription') }}
        </p>
      </div>
    </div>

    <div class="vocabulary-grid">
      <article
        v-for="(item, idx) in vocabulary"
        :key="`${item.word}-${idx}`"
        class="vocabulary-card"
      >
        <div class="vocabulary-card-header">
          <strong>{{ item.word }}</strong>
          <span v-if="item.reading">{{ item.reading }}</span>
          <span v-else-if="item.phonetic">{{ item.phonetic }}</span>
        </div>
        <p class="vocabulary-definition">{{ item.definition_zh }}</p>
        <p class="vocabulary-example">{{ item.example_sentence }}</p>
        <p class="vocabulary-translation">{{ item.example_translation }}</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { VocabularyItem } from '@/types'

defineProps<{ vocabulary: VocabularyItem[] }>()

const { t } = useI18n()
</script>

<style scoped>
.vocabulary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.vocabulary-card {
  padding: 20px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.vocabulary-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.vocabulary-definition,
.vocabulary-example,
.vocabulary-translation {
  margin: 0;
}

.vocabulary-definition {
  color: #0f172a;
  font-weight: 600;
}

.vocabulary-example {
  margin-top: 12px;
  color: #334155;
}

.vocabulary-translation {
  margin-top: 8px;
  color: #64748b;
  font-size: 0.92rem;
}
</style>
