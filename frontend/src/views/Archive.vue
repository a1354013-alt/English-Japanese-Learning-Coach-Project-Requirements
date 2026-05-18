<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <h2 style="margin: 0">{{ t('archive.title') }}</h2>
      <button class="secondary" :disabled="loading" @click="loadLessons">
        {{ t('common.refresh') }}
      </button>
    </div>

    <LoadingState
      v-if="loading && lessons.length === 0"
      panel-class="panel"
      :message="t('archive.loading')"
    />

    <ErrorState
      v-else-if="error"
      panel-class="panel"
      :message="error"
      :retry-label="t('common.retry')"
      @retry="loadLessons"
    />

    <div
      v-if="!loading && !error"
      class="panel grid"
      style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))"
    >
      <div>
        <label>{{ t('common.language') }}</label>
        <select v-model="filters.language">
          <option value="">{{ t('common.all') }}</option>
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
      </div>
      <div>
        <label>{{ t('common.topic') }}</label>
        <input
          v-model="filters.topic"
          :placeholder="t('archive.topicPlaceholder')"
        />
      </div>
      <div class="row center" style="margin-top: 1.6rem">
        <button :disabled="loading" @click="loadLessons">
          {{ t('archive.applyFilters') }}
        </button>
      </div>
    </div>

    <div
      v-if="lessons.length && !loading && !error"
      class="panel grid"
      style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))"
    >
      <div v-for="lesson in lessons" :key="lesson.lesson_id" class="panel">
        <h3 style="margin: 0">{{ lesson.topic }}</h3>
        <p>{{ lesson.language }} / {{ lesson.level }}</p>
        <p>{{ new Date(lesson.generated_at).toLocaleString() }}</p>
        <button class="secondary" @click="viewLesson(lesson.lesson_id)">
          {{ t('archive.viewLesson') }}
        </button>
      </div>
    </div>

    <EmptyState
      v-if="!lessons.length && !loading && !error"
      panel-class="panel"
      :message="t('archive.empty')"
    />

    <div
      v-if="!loading && !error"
      class="panel grid"
      style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))"
    >
      <div>
        <h3>{{ t('archive.excelImport') }}</h3>
        <p style="font-size: 0.85rem; color: #666">
          {{ t('archive.selectLanguageBeforeUpload') }}
        </p>
        <input
          type="file"
          accept=".xlsx"
          :disabled="!filters.language"
          @change="handleExcelUpload"
        />
        <p v-if="!filters.language" style="font-size: 0.75rem; color: #d32f2f">
          {{ t('archive.selectLanguageFirst') }}
        </p>
      </div>
      <div>
        <h3>{{ t('archive.ragUpload') }}</h3>
        <p style="font-size: 0.85rem; color: #666">
          {{ t('archive.selectLanguageBeforeUpload') }}
        </p>
        <input
          type="file"
          accept=".txt,.md,.csv,.pdf"
          :disabled="!filters.language"
          @change="handleRagUpload"
        />
        <p v-if="!filters.language" style="font-size: 0.75rem; color: #d32f2f">
          {{ t('archive.selectLanguageFirst') }}
        </p>
      </div>
    </div>

    <TaskHistory v-if="!loading && !error" />
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import TaskHistory from '@/components/TaskHistory.vue'
import EmptyState from '@/components/state/EmptyState.vue'
import ErrorState from '@/components/state/ErrorState.vue'
import LoadingState from '@/components/state/LoadingState.vue'
import { importApi, lessonApi } from '@/services/api'
import type { Language, LessonListItem } from '@/types'

withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
})

const { t } = useI18n()
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
    console.error(err)
    error.value = t('archive.loadError')
  } finally {
    loading.value = false
  }
}

const viewLesson = (id: string) => {
  void router.push({ name: 'LessonDetail', params: { id } })
}

const resolveImportLanguage = (): Language | null => {
  if (!filters.language) {
    window.alert(t('archive.importLanguageRequired'))
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
  } catch (err) {
    console.error(err)
    error.value = t('archive.excelImportError')
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
  } catch (err) {
    console.error(err)
    error.value = t('archive.ragUploadError')
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

onMounted(loadLessons)
</script>
