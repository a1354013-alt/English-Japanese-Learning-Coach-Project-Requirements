<template>
  <div class="overlay">
    <div class="dialog panel" data-testid="onboarding-dialog">
      <h2>{{ t('onboarding.title') }}</h2>
      <p>{{ t('onboarding.subtitle') }}</p>

      <label>{{ t('onboarding.language') }}</label>
      <select v-model="form.language" :disabled="saving">
        <option value="EN">{{ t('common.english') }}</option>
        <option value="JP">{{ t('common.japanese') }}</option>
      </select>

      <label>{{ t('onboarding.currentLevel') }}</label>
      <select v-model="form.level" :disabled="saving">
        <option v-for="level in levels" :key="level" :value="level">
          {{ level }}
        </option>
      </select>

      <label>{{ t('onboarding.difficultyMode') }}</label>
      <select v-model="form.difficulty" :disabled="saving">
        <option value="easy">{{ t('onboarding.difficulty.easy') }}</option>
        <option value="normal">{{ t('onboarding.difficulty.normal') }}</option>
        <option value="hardcore">
          {{ t('onboarding.difficulty.hardcore') }}
        </option>
      </select>

      <p v-if="error" class="error-text" role="alert">{{ error }}</p>

      <div class="row gap-sm" style="margin-top: 1rem">
        <button
          data-testid="onboarding-start"
          :disabled="saving"
          @click="submit"
        >
          {{ saving ? t('onboarding.saving') : t('onboarding.start') }}
        </button>
        <button
          v-if="error"
          class="secondary"
          :disabled="saving"
          @click="submit"
        >
          {{ t('common.retry') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { progressApi } from '@/services/api'
import type { DifficultyMode, Language } from '@/types'

const emit = defineEmits<{ complete: [] }>()
const { t } = useI18n()
const saving = ref(false)
const error = ref<string | null>(null)
const form = reactive<{
  language: Language
  level: string
  difficulty: DifficultyMode
}>({
  language: 'EN',
  level: 'A1',
  difficulty: 'normal',
})

const levels = computed(() =>
  form.language === 'EN'
    ? ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    : ['N5', 'N4', 'N3', 'N2', 'N1'],
)

const submit = async () => {
  saving.value = true
  error.value = null
  try {
    await progressApi.onboard(form.language, form.level, form.difficulty)
    emit('complete')
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('onboarding.error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  display: grid;
  place-items: center;
  z-index: 30;
}

.dialog {
  width: min(460px, calc(100% - 1rem));
}

label {
  display: block;
  margin: 0.8rem 0 0.25rem;
}

.error-text {
  margin: 0.75rem 0 0;
  color: #b91c1c;
}
</style>
