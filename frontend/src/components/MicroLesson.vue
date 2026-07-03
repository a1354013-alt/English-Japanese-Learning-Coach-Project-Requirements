<template>
  <section class="section-card page-stack" data-testid="micro-lesson">
    <div class="section-header">
      <div>
        <p class="eyebrow">
          {{
            t('microLesson.dayLabel', {
              day: lesson.day_index,
              total: lesson.total_days,
            })
          }}
        </p>
        <h2>{{ t('microLesson.title') }}</h2>
        <p class="section-description">{{ plan?.summary_zh }}</p>
      </div>
      <span class="status-pill" :class="{ done: localLesson.completed }">
        {{
          localLesson.completed
            ? t('microLesson.completed')
            : localLesson.target_exam
        }}
      </span>
    </div>

    <div class="micro-sentence">
      <p>{{ localLesson.sentence }}</p>
      <span>{{ localLesson.translation_zh }}</span>
    </div>

    <div class="micro-grid">
      <div>
        <h3>{{ t('microLesson.breakdown') }}</h3>
        <dl class="breakdown-list">
          <div>
            <dt>{{ t('microLesson.subject') }}</dt>
            <dd>{{ localLesson.subject_text }}</dd>
          </div>
          <div>
            <dt>{{ t('microLesson.verb') }}</dt>
            <dd>{{ localLesson.verb_text }}</dd>
          </div>
          <div>
            <dt>{{ t('microLesson.object') }}</dt>
            <dd>{{ localLesson.object_text }}</dd>
          </div>
        </dl>
      </div>
      <div>
        <h3>{{ t('microLesson.readingOrder') }}</h3>
        <ol>
          <li v-for="step in localLesson.reading_order_steps" :key="step">
            {{ step }}
          </li>
        </ol>
      </div>
    </div>

    <div class="note-grid">
      <p>{{ localLesson.grammar_note }}</p>
      <p>{{ localLesson.toeic_usage_note }}</p>
    </div>

    <section>
      <h3>{{ t('microLesson.vocabulary') }}</h3>
      <div class="vocab-grid">
        <article
          v-for="item in localLesson.vocabulary_items"
          :key="item.word"
          class="vocab-card"
        >
          <strong>{{ item.word }}</strong>
          <span>{{ item.phonetic }} · {{ item.pronunciation_zh }}</span>
          <p>{{ item.definition_zh }}</p>
          <small
            >{{ item.example_sentence }} / {{ item.example_translation }}</small
          >
        </article>
      </div>
    </section>

    <section>
      <h3>{{ t('microLesson.dialogue') }}</h3>
      <p
        v-for="line in localLesson.dialogue_lines"
        :key="`${line.speaker}-${line.english}`"
      >
        <strong>{{ line.speaker }}:</strong> {{ line.english }}
        <span class="muted">/ {{ line.translation_zh }}</span>
      </p>
    </section>

    <section>
      <h3>{{ t('microLesson.reading') }}</h3>
      <p>{{ localLesson.reading_passage }}</p>
    </section>

    <section>
      <h3>{{ t('microLesson.comic') }}</h3>
      <div class="comic-grid">
        <article
          v-for="panel in localLesson.comic_panels"
          :key="panel.panel"
          class="comic-panel"
        >
          <span>{{ panel.panel }}</span>
          <strong>{{ panel.english }}</strong>
          <p>{{ panel.translation_zh }}</p>
        </article>
      </div>
    </section>

    <section class="fill-blank">
      <h3>{{ t('microLesson.fillBlank') }}</h3>
      <p>{{ localLesson.fill_blank_question.prompt }}</p>
      <div class="choice-actions">
        <button
          v-for="choice in localLesson.fill_blank_question.choices"
          :key="choice"
          type="button"
          :class="{ selected: selectedAnswer === choice }"
          @click="selectedAnswer = choice"
        >
          {{ choice }}
        </button>
      </div>
      <button
        data-testid="micro-answer-submit"
        type="button"
        :disabled="submitting || !selectedAnswer"
        @click="submitAnswer"
      >
        {{ submitting ? t('today.submitting') : t('common.submit') }}
      </button>
      <p v-if="answerMessage" class="answer-message">{{ answerMessage }}</p>
    </section>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { microLessonApi } from '@/services/api'
import type { LearningPlan, MicroLesson } from '@/types'

const props = defineProps<{
  lesson: MicroLesson
  plan: LearningPlan | null
}>()

const emit = defineEmits<{
  completed: [lesson: MicroLesson]
}>()

const { t } = useI18n()
const localLesson = reactive<MicroLesson>({ ...props.lesson })
const selectedAnswer = ref('')
const submitting = ref(false)
const answerMessage = ref('')

watch(
  () => props.lesson,
  (nextLesson) => {
    Object.assign(localLesson, nextLesson)
    selectedAnswer.value = ''
    answerMessage.value = ''
  },
)

const submitAnswer = async () => {
  if (!selectedAnswer.value) return
  submitting.value = true
  answerMessage.value = ''
  try {
    const response = await microLessonApi.answer(
      localLesson.lesson_id,
      selectedAnswer.value,
    )
    Object.assign(localLesson, response.lesson)
    answerMessage.value = response.correct
      ? t('microLesson.correct')
      : t('microLesson.incorrect')
    if (response.completed) {
      emit('completed', response.lesson)
    }
  } catch (err) {
    console.error(err)
    answerMessage.value = t('microLesson.answerError')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.eyebrow {
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 4px;
  text-transform: uppercase;
}

.status-pill {
  background: #eef2ff;
  border-radius: 999px;
  color: #3730a3;
  font-weight: 700;
  padding: 8px 12px;
}

.status-pill.done {
  background: #dcfce7;
  color: #166534;
}

.micro-sentence {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 18px;
}

.micro-sentence p {
  font-size: 1.6rem;
  font-weight: 800;
  margin: 0 0 8px;
}

.micro-grid,
.note-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.breakdown-list {
  display: grid;
  gap: 10px;
  margin: 0;
}

.breakdown-list div,
.vocab-card,
.comic-panel {
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 12px;
}

.breakdown-list dt {
  color: #64748b;
  font-size: 0.8rem;
}

.breakdown-list dd {
  font-size: 1.2rem;
  font-weight: 800;
  margin: 0;
}

.note-grid p {
  background: #fff7ed;
  border-radius: 8px;
  margin: 0;
  padding: 12px;
}

.vocab-grid,
.comic-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.vocab-card {
  display: grid;
  gap: 6px;
}

.vocab-card span,
.muted,
.vocab-card small {
  color: #64748b;
}

.comic-panel {
  display: grid;
  gap: 6px;
}

.comic-panel span {
  color: #2563eb;
  font-weight: 800;
}

.choice-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.choice-actions button.selected {
  background: #1d4ed8;
  color: white;
}

.answer-message {
  font-weight: 700;
  margin: 12px 0 0;
}

@media (max-width: 800px) {
  .micro-grid,
  .note-grid {
    grid-template-columns: 1fr;
  }
}
</style>
