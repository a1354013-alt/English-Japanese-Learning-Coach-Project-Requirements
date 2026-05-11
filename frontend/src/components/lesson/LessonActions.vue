<template>
  <div class="bottom-action-bar">
    <div>
      <strong>{{ t('today.bottomBarTitle') }}</strong>
      <p>{{ t('today.bottomBarDescription', { answered: answeredQuestions, total: totalQuestions }) }}</p>
    </div>
    <div class="toolbar">
      <button data-testid="submit-review" :disabled="submitting" @click="$emit('submit-review')">
        {{ submitting ? t('today.submitting') : t('today.submitReview') }}
      </button>
      <button class="secondary" :disabled="exportDisabled || exportingPdf" @click="$emit('export-pdf')">
        {{ exportingPdf ? t('today.exportingPdf') : t('today.exportPdf') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  answeredQuestions: number
  totalQuestions: number
  submitting: boolean
  exportingPdf: boolean
  exportDisabled: boolean
}>()

defineEmits<{
  'submit-review': []
  'export-pdf': []
}>()

const { t } = useI18n()
</script>

<style scoped>
.bottom-action-bar {
  position: sticky;
  bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 18px 20px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 32px rgba(37, 99, 235, 0.08);
}

.bottom-action-bar p {
  margin: 6px 0 0;
  color: #64748b;
}
</style>
