<template>
  <div :class="containerClass" :data-testid="testId">
    <p class="state-message">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    message: string
    panelClass?: string
    testId?: string
  }>(),
  {
    panelClass: 'section-card',
    testId: 'loading-state',
  },
)

const containerClass = computed(() => [props.panelClass, 'state-panel'])
</script>

<style scoped>
.state-panel {
  display: grid;
  place-items: center;
  min-height: 120px;
}

.state-message {
  margin: 0;
  color: #475569;
}
</style>
