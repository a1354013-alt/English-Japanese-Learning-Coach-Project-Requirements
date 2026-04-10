<template>
  <div class="overlay">
    <div class="dialog panel">
      <h2>Welcome</h2>
      <p>Set your initial language and level.</p>

      <label>Language</label>
      <select v-model="form.language">
        <option value="EN">English</option>
        <option value="JP">Japanese</option>
      </select>

      <label>Current Level</label>
      <select v-model="form.level">
        <option v-for="level in levels" :key="level" :value="level">{{ level }}</option>
      </select>

      <label>Difficulty Mode</label>
      <select v-model="form.difficulty">
        <option value="easy">easy</option>
        <option value="normal">normal</option>
        <option value="hardcore">hardcore</option>
      </select>

      <div class="row gap-sm" style="margin-top: 1rem">
        <button :disabled="saving" @click="submit">{{ saving ? 'Saving...' : 'Start' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { progressApi } from '@/services/api'
import type { Language } from '@/types'

const emit = defineEmits<{ complete: [] }>()
const saving = ref(false)
const form = reactive<{ language: Language; level: string; difficulty: string }>({
  language: 'EN',
  level: 'A1',
  difficulty: 'normal',
})

const levels = computed(() => (form.language === 'EN' ? ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] : ['N5', 'N4', 'N3', 'N2', 'N1']))

const submit = async () => {
  saving.value = true
  try {
    await progressApi.onboard(form.language, form.level, form.difficulty)
    emit('complete')
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
</style>
