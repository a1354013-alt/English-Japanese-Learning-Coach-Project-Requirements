<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">Lesson Detail</h2>
      <button class="secondary" @click="$router.push('/archive')">Back to Archive</button>
    </div>

    <div class="panel" v-if="loading">Loading lesson...</div>
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
      </section>

      <section>
        <h3>Reading</h3>
        <p style="white-space: pre-wrap">{{ lesson.reading.content }}</p>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { lessonApi } from '@/services/api'
import type { Lesson } from '@/types'

const route = useRoute()
const loading = ref(true)
const lesson = ref<Lesson | null>(null)

onMounted(async () => {
  try {
    const id = String(route.params.id)
    const res = await lessonApi.getLesson(id)
    lesson.value = res.lesson
  } finally {
    loading.value = false
  }
})
</script>
