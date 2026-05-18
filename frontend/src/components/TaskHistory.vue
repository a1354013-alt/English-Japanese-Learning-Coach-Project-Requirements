<template>
  <section>
    <div class="row between center" style="margin-bottom: 0.75rem">
      <h3 style="margin: 0">{{ t('taskHistory.title') }}</h3>
      <button class="secondary" :disabled="loading" @click="loadTasks">
        {{ loading ? t('taskHistory.loading') : t('common.refresh') }}
      </button>
    </div>
    <p v-if="error" style="color: #b91c1c; margin: 0 0 0.75rem">{{ error }}</p>
    <p v-if="loading && tasks.length === 0">{{ t('taskHistory.loading') }}</p>
    <table
      v-else-if="tasks.length"
      style="width: 100%; border-collapse: collapse"
    >
      <thead>
        <tr>
          <th align="left">{{ t('taskHistory.time') }}</th>
          <th align="left">{{ t('taskHistory.status') }}</th>
          <th align="left">{{ t('taskHistory.model') }}</th>
          <th align="left">{{ t('taskHistory.duration') }}</th>
          <th align="left">{{ t('taskHistory.note') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.task_id">
          <td>{{ new Date(task.created_at).toLocaleString() }}</td>
          <td>
            {{ getTaskStatusLabel(task.status) }}
          </td>
          <td>{{ task.model_used }}</td>
          <td>{{ task.duration_ms }} ms</td>
          <td style="color: #666; font-size: 0.85rem">
            {{ task.error_message ?? '' }}
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else>{{ t('taskHistory.empty') }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { lessonApi } from '@/services/api'
import type { GenerationTask } from '@/types'
import { getTaskStatusLabel } from '@/utils/taskStatusLabel'

const { t } = useI18n()
const tasks = ref<GenerationTask[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const loadTasks = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await lessonApi.getTasks()
    tasks.value = res.tasks
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('taskHistory.error')
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>
