<template>
  <section>
    <div class="row between center" style="margin-bottom: 0.75rem">
      <h3 style="margin: 0">Generation Tasks</h3>
      <button class="secondary" @click="loadTasks" :disabled="loading">{{ loading ? 'Loading...' : 'Refresh' }}</button>
    </div>
    <p v-if="error" style="color: #b91c1c; margin: 0 0 0.75rem">{{ error }}</p>
    <p v-if="loading && tasks.length === 0">Loading task history...</p>
    <table v-else-if="tasks.length" style="width: 100%; border-collapse: collapse">
      <thead>
        <tr>
          <th align="left">Time</th>
          <th align="left">Status</th>
          <th align="left">Model</th>
          <th align="left">Duration</th>
          <th align="left">Note</th>
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
          <td style="color:#666; font-size:0.85rem">{{ task.error_message ?? '' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else>No task history yet.</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { lessonApi } from '@/services/api'
import type { GenerationTask } from '@/types'
import { getTaskStatusLabel } from '@/utils/taskStatusLabel'

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
    error.value = err instanceof Error ? err.message : 'Failed to load generation tasks'
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>
