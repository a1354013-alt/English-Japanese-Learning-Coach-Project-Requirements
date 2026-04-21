<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">Lesson Detail</h2>
      <button class="secondary" @click="$router.push('/archive')">Back to Archive</button>
    </div>

    <div class="panel" v-if="loading">Loading lesson…</div>
    <div class="panel" v-else-if="error">
      <p class="error-text">{{ error }}</p>
      <button type="button" @click="loadLesson">Retry</button>
    </div>
    <div class="panel" v-else-if="!lesson">Lesson not found.</div>

    <div v-else class="grid">
      <section>
        <h3>{{ lesson.metadata.topic }}</h3>
        <p>{{ lesson.metadata.language }} / {{ lesson.metadata.level }}</p>
        <p>{{ new Date(lesson.metadata.generated_at).toLocaleString('zh-TW') }}</p>
      </section>

      <section>
        <h3>Vocabulary</h3>
        <ul>
          <li v-for="(item, index) in lesson.vocabulary" :key="index">
            {{ item.word }} - {{ item.definition_zh }}
          </li>
        </ul>
      </section>

      <section>
        <h3>Grammar</h3>
        <p>{{ lesson.grammar.title }}</p>
        <p>{{ lesson.grammar.explanation }}</p>
        <div v-if="lesson.grammar.exercises && lesson.grammar.exercises.length > 0">
          <h4>Grammar Exercises</h4>
          <ul>
            <li v-for="(ex, idx) in lesson.grammar.exercises" :key="idx">
              {{ ex.question }}
              <br/>
              <small>Answer: {{ ex.correct_answer }}</small>
            </li>
          </ul>
        </div>
      </section>

      <section>
        <h3>Reading</h3>
        <p style="white-space: pre-wrap">{{ lesson.reading.content }}</p>
        <div v-if="lesson.reading.questions && lesson.reading.questions.length > 0">
          <h4>Reading Questions</h4>
          <ol>
            <li v-for="(q, idx) in lesson.reading.questions" :key="idx">
              <div>{{ q.question }}</div>
              <small>Answer: {{ q.correct_answer }}</small>
            </li>
          </ol>
        </div>
      </section>

      <section v-if="lesson.dialogue">
        <h3>Dialogue</h3>
        <p v-if="lesson.dialogue.scenario">{{ lesson.dialogue.scenario }}</p>
        <p v-if="lesson.dialogue.context" style="color: #64748b">{{ lesson.dialogue.context }}</p>
        <div
          v-for="(line, idx) in lesson.dialogue.dialogue"
          :key="idx"
          style="margin-bottom: 0.5rem"
        >
          <strong>{{ line.speaker }}:</strong> {{ line.text }}
        </div>
      </section>

      <RagEvidencePanel v-if="lesson.evidence" :evidence="lesson.evidence" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { lessonApi } from '@/services/api'
import type { Lesson } from '@/types'
import RagEvidencePanel from '@/components/RagEvidencePanel.vue'

const route = useRoute()
const loading = ref(true)
const error = ref<string | null>(null)
const lesson = ref<Lesson | null>(null)

const loadLesson = async () => {
  loading.value = true
  error.value = null
  lesson.value = null
  try {
    const id = String(route.params.id)
    const res = await lessonApi.getLesson(id)
    lesson.value = res.lesson
  } catch {
    error.value = 'Could not load this lesson. It may have been removed or the API is unavailable.'
  } finally {
    loading.value = false
  }
}

onMounted(loadLesson)
watch(
  () => route.params.id,
  () => {
    void loadLesson()
  },
)
</script>

<style scoped>
.error-text {
  color: #b91c1c;
  margin: 0 0 0.75rem;
}
</style>
