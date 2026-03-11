<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="bg-mesh"></div>
    
    <!-- Header -->
    <div class="flex justify-between items-center mb-8 animate__animated animate__fadeIn">
      <div>
        <h1 class="text-4xl font-black text-white tracking-tight">AI 寫作中心</h1>
        <p class="text-slate-400 mt-1">提升您的寫作技巧，獲得專業 AI 批改反饋</p>
      </div>
      <div class="flex gap-3">
        <select v-model="submission.language" class="glass-panel px-4 py-2 rounded-xl text-sm font-bold text-white bg-transparent border-none outline-none">
          <option value="EN">English</option>
          <option value="JP">日本語</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <!-- Left: Editor -->
      <div class="lg:col-span-7 space-y-6">
        <div class="glass-panel p-6 rounded-3xl">
          <div class="mb-4">
            <label class="block text-sm font-bold text-slate-400 mb-2">主題 (選填)</label>
            <input v-model="submission.topic" class="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-blue-500 outline-none transition-all" placeholder="例如：我的夢想、昨天的旅行..." />
          </div>
          <div class="mb-6">
            <label class="block text-sm font-bold text-slate-400 mb-2">內容</label>
            <textarea 
              v-model="submission.text" 
              rows="12" 
              class="w-full bg-slate-900/50 border border-white/10 rounded-2xl px-4 py-4 text-white focus:border-blue-500 outline-none transition-all resize-none font-serif text-lg leading-relaxed"
              placeholder="在此輸入您的文章..."
            ></textarea>
            <div class="text-right text-xs text-slate-500 mt-2">字數：{{ submission.text.length }}</div>
          </div>
          <button 
            @click="analyzeWriting" 
            :disabled="loading || !submission.text"
            class="w-full btn-3d bg-blue-600 py-4 rounded-2xl font-bold text-white flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <i v-if="loading" class="pi pi-spin pi-spinner"></i>
            {{ loading ? 'AI 正在深度批改中...' : '提交批改' }}
          </button>
        </div>
      </div>

      <!-- Right: Analysis Results -->
      <div class="lg:col-span-5">
        <div v-if="!analysis && !loading" class="glass-panel p-8 rounded-3xl h-full flex flex-col items-center justify-center text-center">
          <div class="w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mb-6">
            <i class="pi pi-pencil text-3xl text-blue-400"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">準備好開始了嗎？</h3>
          <p class="text-slate-400 text-sm">輸入您的文章並點擊提交，AI 導師將為您提供詳細的語法、詞彙與風格分析。</p>
        </div>

        <div v-if="loading" class="glass-panel p-8 rounded-3xl h-full flex flex-col items-center justify-center text-center">
          <div class="w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mb-6 animate-pulse">
            <i class="pi pi-sparkles text-3xl text-blue-400"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">正在分析...</h3>
          <p class="text-slate-400 text-sm">AI 正在檢查語法、評估等級並準備改進建議。</p>
        </div>

        <div v-if="analysis" class="space-y-6 animate__animated animate__fadeIn">
          <!-- Scores -->
          <div class="glass-panel p-6 rounded-3xl">
            <div class="flex justify-between items-center mb-6">
              <h3 class="font-bold text-white">評分報告</h3>
              <span class="px-3 py-1 rounded-lg bg-blue-600 text-white text-xs font-bold">{{ analysis.estimated_level }}</span>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div v-for="(score, label) in { '語法': analysis.grammar_score, '詞彙': analysis.vocabulary_score, '風格': analysis.style_score, '總分': analysis.overall_score }" :key="label" class="text-center p-3 rounded-2xl bg-white/5">
                <div class="text-2xl font-black text-blue-400">{{ score }}</div>
                <div class="text-[10px] text-slate-500 uppercase font-bold">{{ label }}</div>
              </div>
            </div>
          </div>

          <!-- Feedback -->
          <div class="glass-panel p-6 rounded-3xl">
            <h3 class="font-bold text-white mb-3">導師評語</h3>
            <p class="text-sm text-slate-300 leading-relaxed">{{ analysis.feedback }}</p>
          </div>

          <!-- Corrections -->
          <div class="glass-panel p-6 rounded-3xl">
            <h3 class="font-bold text-white mb-4">重點修正</h3>
            <div class="space-y-4">
              <div v-for="(corr, idx) in analysis.corrections.slice(0, 3)" :key="idx" class="p-3 rounded-xl bg-red-500/5 border border-red-500/10">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-red-500/20 text-red-400">{{ corr.type }}</span>
                </div>
                <div class="text-sm line-through text-slate-500">{{ corr.original }}</div>
                <div class="text-sm text-green-400 font-bold">→ {{ corr.corrected }}</div>
                <div class="text-[11px] text-slate-400 mt-1 italic">{{ corr.explanation }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import api from '@/services/api';
import confetti from 'canvas-confetti';

const loading = ref(false);
const analysis = ref<any>(null);

const submission = ref({
  language: 'EN',
  text: '',
  topic: '',
  target_level: ''
});

const analyzeWriting = async () => {
  loading.value = true;
  analysis.value = null;
  try {
    const res = await api.post('/writing/analyze', submission.value);
    if (res.data.success) {
      analysis.value = res.data.analysis;
      if (analysis.value.overall_score >= 80) {
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 }
        });
      }
    }
  } catch (e) {
    alert('批改失敗，請稍後再試。');
    console.error(e);
  } finally {
    loading.value = false;
  }
};
</script>
