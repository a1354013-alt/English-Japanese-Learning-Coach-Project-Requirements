<template>
  <div :class="containerClass" :data-testid="testId">
    <p class="state-message">{{ message }}</p>
    <p v-if="hint" class="state-hint">{{ hint }}</p>
    <button
      v-if="actionLabel"
      :class="buttonClass"
      type="button"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    message: string
    hint?: string
    actionLabel?: string
    panelClass?: string
    buttonClass?: string
    testId?: string
  }>(),
  {
    hint: '',
    actionLabel: '',
    panelClass: 'section-card',
    buttonClass: '',
    testId: 'empty-state',
  },
)

defineEmits<{
  action: []
}>()

const containerClass = computed(() => [props.panelClass, 'state-panel'])
</script>

<style scoped>
.state-panel {
  display: grid;
  gap: 8px;
}

.state-message,
.state-hint {
  margin: 0;
}

.state-message {
  color: #334155;
}

.state-hint {
  color: #64748b;
}
</style>
