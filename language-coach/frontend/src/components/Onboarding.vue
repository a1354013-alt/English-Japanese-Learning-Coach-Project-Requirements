<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
    <div class="glass-panel max-w-2xl w-full p-8 animate__animated animate__fadeInUp">
      <h2 class="text-3xl font-bold mb-6 text-center bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
        歡迎來到 AI 語言冒險！
      </h2>
      
      <div v-if="step === 1" class="space-y-6">
        <p class="text-gray-300 text-center text-lg">首先，你想學習哪種語言？</p>
        <div class="grid grid-cols-2 gap-4">
          <button @click="selectLanguage('EN')" :class="['p-6 rounded-xl border-2 transition-all', form.language === 'EN' ? 'border-blue-500 bg-blue-500/20' : 'border-gray-700 hover:border-blue-400']">
            <div class="text-4xl mb-2">🇺🇸</div>
            <div class="font-bold">English</div>
          </button>
          <button @click="selectLanguage('JP')" :class="['p-6 rounded-xl border-2 transition-all', form.language === 'JP' ? 'border-red-500 bg-red-500/20' : 'border-gray-700 hover:border-red-400']">
            <div class="text-4xl mb-2">🇯🇵</div>
            <div class="font-bold">日本語</div>
          </button>
        </div>
      </div>

      <div v-if="step === 2" class="space-y-6">
        <p class="text-gray-300 text-center text-lg">你的目前程度是？</p>
        <div class="grid grid-cols-3 gap-3">
          <button v-for="lvl in levels" :key="lvl" @click="form.level = lvl" 
            :class="['p-3 rounded-lg border transition-all', form.level === lvl ? 'bg-purple-500 border-purple-400' : 'bg-gray-800 border-gray-700']">
            {{ lvl }}
          </button>
        </div>
      </div>

      <div v-if="step === 3" class="space-y-6">
        <p class="text-gray-300 text-center text-lg">選擇你的學習模式</p>
        <div class="space-y-3">
          <button v-for="mode in modes" :key="mode.id" @click="form.difficulty = mode.id"
            :class="['w-full p-4 rounded-xl border-2 text-left transition-all', form.difficulty === mode.id ? 'border-green-500 bg-green-500/10' : 'border-gray-700']">
            <div class="font-bold">{{ mode.name }}</div>
            <div class="text-sm text-gray-400">{{ mode.desc }}</div>
          </button>
        </div>
      </div>

      <div class="mt-8 flex justify-between">
        <button v-if="step > 1" @click="step--" class="px-6 py-2 text-gray-400 hover:text-white">上一步</button>
        <div v-else></div>
        <button @click="nextStep" class="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full font-bold hover:scale-105 transition-transform">
          {{ step === 3 ? '開始冒險！' : '下一步' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import axios from 'axios';

const emit = defineEmits(['complete']);
const step = ref(1);
const form = ref({
  language: 'EN',
  level: 'A1',
  difficulty: 'normal'
});

const levels = computed(() => form.value.language === 'EN' ? ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] : ['N5', 'N4', 'N3', 'N2', 'N1']);

const modes = [
  { id: 'easy', name: '☕ 輕鬆模式', desc: '適合碎片時間，內容較短且簡單。' },
  { id: 'normal', name: '📚 正常模式', desc: '平衡的學習強度，適合每日進修。' },
  { id: 'hardcore', name: '🔥 硬核模式', desc: '高強度挑戰，包含更多進階文法與長文。' }
];

const selectLanguage = (lang) => {
  form.value.language = lang;
  form.value.level = lang === 'EN' ? 'A1' : 'N5';
};

const nextStep = async () => {
  if (step.value < 3) {
    step.value++;
  } else {
    try {
      await axios.post('http://localhost:8000/api/onboard', form.value);
      emit('complete');
    } catch (e) {
      console.error(e);
    }
  }
};
</script>
