<template>
  <div
    v-if="dialogue.dialogue.length"
    class="section-card"
    data-testid="lesson-dialogue"
  >
    <div class="section-header">
      <div>
        <h2>對話</h2>
        <p class="section-description">{{ dialogue.scenario }}</p>
      </div>
    </div>
    <p v-if="dialogue.context" class="context">{{ dialogue.context }}</p>
    <div class="page-stack">
      <div v-for="(line, index) in dialogue.dialogue" :key="index" class="line">
        <strong>{{ line.speaker }}</strong>
        <span>{{ line.text }}</span>
        <small>{{ line.translation }}</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DialogueSection } from '@/types'

defineProps<{ dialogue: DialogueSection }>()
</script>

<style scoped>
.context {
  margin: 0 0 16px;
  color: #64748b;
}

.line {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 8px 16px;
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
}

.line small {
  grid-column: 2;
  color: #64748b;
}

@media (max-width: 700px) {
  .line {
    grid-template-columns: 1fr;
  }

  .line small {
    grid-column: 1;
  }
}
</style>
