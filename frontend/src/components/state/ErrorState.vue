<template>
  <div :class="containerClass" :data-testid="testId">
    <p class="state-error">{{ message }}</p>
    <button
      v-if="retryLabel"
      :class="buttonClass"
      type="button"
      @click="$emit('retry')"
    >
      {{ retryLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    message: string
    retryLabel?: string
    panelClass?: string
    buttonClass?: string
    testId?: string
  }>(),
  {
    retryLabel: '',
    panelClass: 'section-card',
    buttonClass: 'secondary',
    testId: 'error-state',
  },
)

defineEmits<{
  retry: []
}>()

const containerClass = computed(() => [props.panelClass, 'state-panel'])
</script>

<style scoped>
.state-panel {
  display: grid;
  gap: 12px;
}

.state-error {
  margin: 0;
  color: #b91c1c;
}
</style>
