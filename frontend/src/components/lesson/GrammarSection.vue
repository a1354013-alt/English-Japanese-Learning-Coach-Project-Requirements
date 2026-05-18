<template>
  <div class="section-card" data-testid="lesson-grammar">
    <div class="section-header">
      <div>
        <h2>{{ t('today.grammarExercises') }}</h2>
        <p class="section-description">{{ grammar.title }}</p>
      </div>
    </div>

    <div class="grammar-explainer surface-muted">
      <p>{{ grammar.explanation }}</p>
    </div>

    <div class="page-stack">
      <article
        v-for="(exercise, index) in grammar.exercises"
        :key="`g-${index}`"
        class="question-card"
        :data-testid="`grammar-exercise-${index}`"
      >
        <p class="question-title">
          <strong>{{ index + 1 }}. {{ exercise.question }}</strong>
        </p>
        <div v-if="exercise.options?.length" class="choice-list">
          <label
            v-for="(option, optionIndex) in exercise.options"
            :key="option"
            class="choice-card"
          >
            <input
              type="radio"
              :name="`g-${index}`"
              :value="option"
              :checked="answers[index] === option"
              :data-testid="`grammar-option-${index}-${optionIndex}`"
              @change="emitAnswer(index, option)"
            />
            <span>{{ option }}</span>
          </label>
        </div>
        <input
          v-else
          :value="answers[index] ?? ''"
          :placeholder="t('today.yourAnswer')"
          :data-testid="`grammar-input-${index}`"
          @input="emitInput(index, $event)"
        />
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { GrammarSection } from '@/types'

defineProps<{
  grammar: GrammarSection
  answers: Record<number, string>
}>()

const emit = defineEmits<{
  'update-answer': [index: number, value: string]
}>()

const { t } = useI18n()

const emitAnswer = (index: number, value: string) => {
  emit('update-answer', index, value)
}

const emitInput = (index: number, event: Event) => {
  emit('update-answer', index, (event.target as HTMLInputElement).value)
}
</script>

<style scoped>
.grammar-explainer {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  margin-bottom: 20px;
}

.grammar-explainer p {
  margin: 0;
  color: #334155;
}

.question-card {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.question-title {
  margin: 0 0 16px;
}

.choice-list {
  display: grid;
  gap: 12px;
}

.choice-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: #f8fbff;
  cursor: pointer;
}

.choice-card input {
  width: auto;
  margin: 0;
}
</style>
