<template>
  <section class="evidence-panel" v-if="evidence && evidence.length > 0">
    <h4>Evidence Sources</h4>
    <ul class="evidence-list">
      <li v-for="(item, idx) in evidence" :key="idx" class="evidence-item">
        <span class="source-badge">{{ item.source }}</span>
        <span class="chunk-info">chunk {{ item.chunk_index + 1 }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
interface EvidenceItem {
  source: string
  chunk_index: number
}

defineProps<{
  evidence?: EvidenceItem[]
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
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.evidence-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
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
</style>
