<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">Lesson Archive</h2>
      <button class="secondary" @click="loadLessons" :disabled="loading">Refresh</button>
    </div>

    <!-- Loading State -->
    <div class="panel" v-if="loading && lessons.length === 0">
      <p>Loading lessons...</p>
    </div>

    <!-- Error State -->
    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button @click="loadLessons" class="secondary">Retry</button>
    </div>

    <!-- Filter Panel -->
    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))" v-if="!loading && !error">
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
        <button @click="loadLessons" :disabled="loading">Apply Filters</button>
      </div>
    </div>

    <!-- Lessons Grid -->
    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))" v-if="lessons.length && !loading && !error">
      <div class="panel" v-for="lesson in lessons" :key="lesson.lesson_id">
        <h3 style="margin: 0">{{ lesson.topic }}</h3>
        <p>{{ lesson.language }} / {{ lesson.level }}</p>
        <p>{{ new Date(lesson.generated_at).toLocaleString('zh-TW') }}</p>
        <button class="secondary" @click="viewLesson(lesson.lesson_id)">View Lesson</button>
      </div>
    </div>

    <!-- Empty State -->
    <div class="panel" v-if="!lessons.length && !loading && !error">
      <p>No lessons found. Generate your first lesson to get started!</p>
    </div>

    <!-- Import Section -->
    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))" v-if="!loading && !error">
      <div>
        <h3>Excel Import</h3>
        <p style="font-size: 0.85rem; color: #666">Select language before uploading</p>
        <input type="file" accept=".xlsx,.xls" @change="handleExcelUpload" :disabled="!filters.language" />
        <p v-if="!filters.language" style="font-size: 0.75rem; color: #d32f2f">Please select a language first</p>
      </div>
      <div>
        <h3>RAG Upload</h3>
        <p style="font-size: 0.85rem; color: #666">Select language before uploading</p>
        <input type="file" accept=".txt,.md,.csv" @change="handleRagUpload" :disabled="!filters.language" />
        <p v-if="!filters.language" style="font-size: 0.75rem; color: #d32f2f">Please select a language first</p>
      </div>
    </div>

    <TaskHistory v-if="!loading && !error" />
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
const loading = ref(false)
const error = ref<string | null>(null)

const filters = reactive<{ language: '' | Language; topic: string }>({
  language: '',
  topic: '',
})

const loadLessons = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await lessonApi.listLessons({
      language: filters.language || undefined,
      topic: filters.topic || undefined,
      limit: 100,
    })
    lessons.value = res.lessons
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load lessons'
  } finally {
    loading.value = false
  }
}

const viewLesson = (id: string) => {
  void router.push({ name: 'LessonDetail', params: { id } })
}

const resolveImportLanguage = (): Language | null => {
  if (!filters.language) {
    window.alert('請先選擇語言（English 或 Japanese），不可使用「All」。')
    return null
  }
  return filters.language
}

const handleExcelUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const lang = resolveImportLanguage()
  if (!lang) return
  try {
    await importApi.importExcel(lang, file)
    await loadLessons()
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

const handleRagUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const lang = resolveImportLanguage()
  if (!lang) return
  try {
    await importApi.uploadRagMaterial(lang, file)
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

onMounted(loadLessons)
</script>
