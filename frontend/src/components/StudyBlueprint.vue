<template>
  <div class="glass-panel p-8 rounded-3xl animate__animated animate__fadeIn">
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-2xl font-black text-white">AI 學習藍圖</h2>
        <p class="text-slate-400 text-sm">根據您的目標與進度動態生成的個人化路徑</p>
      </div>
      <div v-if="!plan" class="flex gap-2">
        <input v-model="targetGoal" class="bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white text-sm outline-none focus:border-blue-500" placeholder="例如：TOEIC 800" />
        <button @click="generatePlan" :disabled="loading" class="btn-3d bg-blue-600 px-6 py-2 rounded-xl text-sm font-bold text-white">
          {{ loading ? '生成中...' : '生成計畫' }}
        </button>
      </div>
      <button v-else @click="plan = null" class="text-slate-500 hover:text-white text-sm font-bold transition-colors">重新設定</button>
    </div>

    <div v-if="loading" class="py-20 flex flex-col items-center justify-center">
      <div class="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-4"></div>
      <p class="text-slate-400 animate-pulse">AI 正在分析您的數據並規劃最佳路徑...</p>
    </div>

    <div v-else-if="plan" class="space-y-8">
      <!-- Plan Summary -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="p-4 rounded-2xl bg-white/5 border border-white/5">
          <div class="text-xs text-slate-500 font-bold uppercase mb-1">目標</div>
          <div class="text-lg font-black text-white">{{ plan.target_goal }}</div>
        </div>
        <div class="p-4 rounded-2xl bg-white/5 border border-white/5">
          <div class="text-xs text-slate-500 font-bold uppercase mb-1">每日投入</div>
          <div class="text-lg font-black text-blue-400">{{ plan.daily_commitment_minutes }} 分鐘</div>
        </div>
        <div class="p-4 rounded-2xl bg-white/5 border border-white/5">
          <div class="text-xs text-slate-500 font-bold uppercase mb-1">預計完成</div>
          <div class="text-lg font-black text-purple-400">{{ formatDate(plan.end_date) }}</div>
        </div>
      </div>

      <!-- Milestones Timeline -->
      <div class="relative pl-8 space-y-12 before:content-[''] before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-blue-500 before:to-purple-500">
        <div v-for="(milestone, idx) in plan.milestones" :key="idx" class="relative">
          <div class="absolute -left-[29px] top-1 w-5 h-5 rounded-full bg-slate-900 border-4 border-blue-500 z-10"></div>
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 class="text-lg font-bold text-white">{{ milestone.title }}</h3>
              <p class="text-sm text-slate-400 mt-1">{{ milestone.description }}</p>
              <div class="flex flex-wrap gap-2 mt-3">
                <span v-for="skill in milestone.required_skills" :key="skill" class="px-2 py-0.5 rounded-md bg-white/5 text-[10px] font-bold text-slate-300 border border-white/10">
                  # {{ skill }}
                </span>
              </div>
            </div>
            <div class="text-right">
              <div class="text-xs font-bold text-blue-400 mb-1">{{ formatDate(milestone.target_date) }}</div>
              <div class="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase tracking-wider">Phase {{ idx + 1 }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="py-12 text-center">
      <div class="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
        <i class="pi pi-map text-2xl text-slate-600"></i>
      </div>
      <p class="text-slate-500">尚未設定學習目標。輸入您的目標（如：TOEIC 800）來生成專屬藍圖。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import axios from 'axios';

const props = defineProps<{
  language: string
}>();

const loading = ref(false);
const plan = ref<any>(null);
const targetGoal = ref('');

const generatePlan = async () => {
  if (!targetGoal.value) return;
  loading.value = true;
  try {
    const res = await axios.post(`http://localhost:8000/api/study-plan/generate?target_goal=${targetGoal.value}&language=${props.language}`);
    if (res.data.success) {
      plan.value = res.data.plan;
    }
  } catch (e) {
    console.error(e);
    alert('生成計畫失敗，請稍後再試。');
  } finally {
    loading.value = false;
  }
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-TW', { year: 'numeric', month: 'long', day: 'numeric' });
};
</script>
