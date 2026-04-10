<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">Lesson Archive</h2>
      <button class="secondary" @click="loadLessons">Refresh</button>
    </div>

    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))">
      <div>
        <label>Language</label>
        <select v-model="filters.language">
          <option value="">All</option>
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
      </div>
      <div>
        <label>Topic</label>
        <input v-model="filters.topic" placeholder="Filter by topic" />
      </div>
      <div class="row center" style="margin-top: 1.6rem">
        <button @click="loadLessons">Apply Filters</button>
      </div>
    </div>

    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))" v-if="lessons.length">
      <div class="panel" v-for="lesson in lessons" :key="lesson.lesson_id">
        <h3 style="margin: 0">{{ lesson.topic }}</h3>
        <p>{{ lesson.language }} / {{ lesson.level }}</p>
        <p>{{ new Date(lesson.generated_at).toLocaleString('zh-TW') }}</p>
        <button class="secondary" @click="viewLesson(lesson.lesson_id)">View Lesson</button>
      </div>
    </div>
    <div class="panel" v-else>No lessons found.</div>

    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))">
      <div>
        <h3>Excel Import</h3>
        <input type="file" accept=".xlsx,.xls" @change="handleExcelUpload" />
      </div>
      <div>
        <h3>RAG Upload</h3>
        <input type="file" accept=".txt,.md,.csv" @change="handleRagUpload" />
      </div>
    </div>

    <TaskHistory />
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import TaskHistory from '@/components/TaskHistory.vue'
import { importApi, lessonApi } from '@/services/api'
import type { Language } from '@/types'

interface LessonListItem {
  lesson_id: string
  language: Language
  level: string
  topic: string
  generated_at: string
  key_points: string[] | string
}

const router = useRouter()
const lessons = ref<LessonListItem[]>([])

const filters = reactive<{ language: '' | Language; topic: string }>({
  language: '',
  topic: '',
})

const loadLessons = async () => {
  const res = await lessonApi.listLessons({
    language: filters.language || undefined,
    topic: filters.topic || undefined,
    limit: 100,
  })
  lessons.value = res.lessons
}

const viewLesson = (id: string) => {
  void router.push({ name: 'LessonDetail', params: { id } })
}

const handleExcelUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  await importApi.importExcel('EN', file)
  await loadLessons()
}

const handleRagUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  await importApi.uploadRagMaterial('EN', file)
}

onMounted(loadLessons)
</script>
