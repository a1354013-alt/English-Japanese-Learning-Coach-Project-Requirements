<template>
  <section>
    <h3>Generation Tasks</h3>
    <button class="secondary" @click="loadTasks" style="margin-bottom: 0.75rem">Refresh</button>
    <table v-if="tasks.length" style="width: 100%; border-collapse: collapse">
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
          <td>{{ new Date(task.created_at).toLocaleString('zh-TW') }}</td>
          <td>
            <span v-if="task.status === 'fallback_success'">fallback_success</span>
            <span v-else>{{ task.status }}</span>
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

const tasks = ref<GenerationTask[]>([])

const loadTasks = async () => {
  const res = await lessonApi.getTasks()
  tasks.value = res.tasks
}

onMounted(loadTasks)
</script>
