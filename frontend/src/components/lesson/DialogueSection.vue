<template>
  <div
    v-if="safeDialogue.dialogue.length"
    class="section-card"
    data-testid="lesson-dialogue"
  >
    <div class="section-header">
      <div>
        <h2>{{ t('lessonSections.dialogue.title') }}</h2>
        <p class="section-description">{{ safeDialogue.scenario }}</p>
      </div>
    </div>
    <p v-if="safeDialogue.context" class="context">
      {{ safeDialogue.context }}
    </p>
    <div class="page-stack">
      <div
        v-for="(line, index) in safeDialogue.dialogue"
        :key="index"
        class="line"
      >
        <strong>{{ line.speaker }}</strong>
        <span>{{ line.text }}</span>
        <small>{{ line.translation }}</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DialogueSection } from '@/types'

const props = defineProps<{ dialogue?: DialogueSection }>()
const { t } = useI18n()

const safeDialogue = computed<DialogueSection>(() => ({
  scenario: props.dialogue?.scenario ?? '',
  context: props.dialogue?.context ?? '',
  dialogue: props.dialogue?.dialogue ?? [],
  alternatives: props.dialogue?.alternatives ?? [],
}))
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
