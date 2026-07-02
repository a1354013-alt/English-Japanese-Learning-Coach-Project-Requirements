<template>
  <div
    v-if="safeWordRoots.length"
    class="section-card"
    data-testid="lesson-word-roots"
  >
    <div class="section-header">
      <div>
        <h2>{{ t('lessonSections.wordRoots.title') }}</h2>
        <p class="section-description">
          {{ t('lessonSections.wordRoots.description') }}
        </p>
      </div>
    </div>
    <div class="root-grid">
      <article v-for="item in safeWordRoots" :key="item.root" class="mini-card">
        <h3>{{ item.root }}</h3>
        <p class="strong">{{ item.meaning_zh }}</p>
        <p>{{ item.examples.join(' / ') }}</p>
        <p class="muted">{{ item.memory_tip }}</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WordRoot } from '@/types'

const props = defineProps<{ wordRoots?: WordRoot[] }>()
const { t } = useI18n()

const safeWordRoots = computed(() => props.wordRoots ?? [])
</script>

<style scoped>
.root-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.mini-card {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.mini-card h3,
.mini-card p {
  margin: 0;
}

.mini-card p {
  margin-top: 8px;
}

.strong {
  font-weight: 700;
  color: #0f172a;
}

.muted {
  color: #64748b;
}
</style>
