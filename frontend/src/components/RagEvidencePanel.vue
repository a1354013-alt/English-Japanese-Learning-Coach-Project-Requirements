<template>
  <section class="evidence-panel" v-if="evidence && evidence.length > 0">
    <h4>{{ t('evidence.title') }}</h4>
    <ul class="evidence-list">
      <li v-for="(item, idx) in evidence" :key="`${item.material_id}-${item.chunk_index}-${idx}`" class="evidence-item">
        <div class="evidence-topline">
          <span class="source-badge">{{ item.title || item.source }}</span>
          <span class="chunk-info">{{ t('evidence.chunk', { index: item.chunk_index + 1 }) }} / {{ item.total_chunks }}</span>
        </div>
        <p class="evidence-meta">
          {{ item.language || 'N/A' }} · {{ item.source_type || 'text' }} · {{ item.material_id }}
        </p>
        <p class="evidence-text">{{ item.text }}</p>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { LessonEvidence } from '@/types'

const { t } = useI18n()

defineProps<{
  evidence?: LessonEvidence[]
}>()
</script>

<style scoped>
.evidence-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-top: 1rem;
}

.evidence-panel h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.evidence-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.75rem;
}

.evidence-item {
  display: grid;
  gap: 0.35rem;
  font-size: 0.8rem;
  padding: 0.75rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.evidence-topline {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.source-badge {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.chunk-info {
  color: #64748b;
  font-style: italic;
}

.evidence-meta,
.evidence-text {
  margin: 0;
}

.evidence-meta {
  color: #64748b;
}

.evidence-text {
  color: #0f172a;
  white-space: pre-wrap;
}
</style>
