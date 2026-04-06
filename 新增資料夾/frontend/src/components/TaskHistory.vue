<template>
  <div class="glass-panel p-6 mt-8">
    <h3 class="text-xl font-bold mb-4 flex items-center">
      <span class="mr-2">🕒</span> 系統生成日誌 (Stability Tracking)
    </h3>
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="text-gray-400 border-b border-gray-700">
            <th class="pb-2">時間</th>
            <th class="pb-2">狀態</th>
            <th class="pb-2">模型</th>
            <th class="pb-2">耗時</th>
            <th class="pb-2">備註</th>
          </tr>
        </thead>
        <tbody class="text-sm">
          <tr v-for="task in tasks" :key="task.task_id" class="border-b border-gray-800/50">
            <td class="py-3">{{ formatDate(task.created_at) }}</td>
            <td class="py-3">
              <span :class="statusClass(task.status)" class="px-2 py-1 rounded-full text-xs">
                {{ task.status }}
              </span>
            </td>
            <td class="py-3 text-gray-300">{{ task.model_used }}</td>
            <td class="py-3">{{ task.duration_ms }}ms</td>
            <td class="py-3 text-xs text-gray-500">{{ task.error_message || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { lessonApi } from '../services/api';

const tasks = ref([]);

const fetchTasks = async () => {
  try {
    const res = await lessonApi.getTasks();
    if (res.success) {
      tasks.value = res.tasks;
    }
  } catch (e) {
    console.error(e);
  }
};

const formatDate = (dateStr) => {
  const d = new Date(dateStr);
  return d.toLocaleString();
};

const statusClass = (status) => {
  switch (status) {
    case 'success': return 'bg-green-500/20 text-green-400';
    case 'failed': return 'bg-red-500/20 text-red-400';
    case 'running': return 'bg-blue-500/20 text-blue-400';
    case 'retried': return 'bg-yellow-500/20 text-yellow-400';
    default: return 'bg-gray-500/20 text-gray-400';
  }
};

onMounted(fetchTasks);
</script>
