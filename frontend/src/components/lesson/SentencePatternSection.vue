<template>
  <div
    v-if="safeSentencePatterns.length"
    class="section-card"
    data-testid="lesson-sentence-patterns"
  >
    <div class="section-header">
      <div>
        <h2>{{ t('lessonSections.sentencePatterns.title') }}</h2>
        <p class="section-description">
          {{ t('lessonSections.sentencePatterns.description') }}
        </p>
      </div>
    </div>
    <div class="page-stack">
      <article
        v-for="item in safeSentencePatterns"
        :key="item.pattern"
        class="pattern-card"
      >
        <h3>{{ item.pattern }}</h3>
        <p class="strong">{{ item.meaning_zh }}</p>
        <p>{{ item.usage_note }}</p>
        <ul>
          <li v-for="example in item.examples" :key="example.sentence">
            <span>{{ example.sentence }}</span>
            <small>{{ example.translation }}</small>
          </li>
        </ul>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { SentencePattern } from '@/types'

const props = defineProps<{ sentencePatterns?: SentencePattern[] }>()
const { t } = useI18n()

const safeSentencePatterns = computed(() => props.sentencePatterns ?? [])
</script>

<style scoped>
.pattern-card {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.pattern-card h3,
.pattern-card p {
  margin: 0;
}

.pattern-card p,
.pattern-card ul {
  margin-top: 8px;
}

.pattern-card li {
  margin-top: 6px;
}

.pattern-card small {
  display: block;
  color: #64748b;
}

.strong {
  font-weight: 700;
}
</style>
