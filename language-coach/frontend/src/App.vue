<template>
  <div class="min-h-screen flex flex-col relative">
    <!-- 動態背景 -->
    <div class="bg-mesh"></div>
    
    <!-- Navigation -->
    <nav class="glass-panel sticky top-0 z-50 border-b border-white/5">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          <div class="flex items-center gap-2 group cursor-pointer" @click="$router.push('/')">
            <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-900/20 group-hover:scale-110 transition-transform">
              <i class="pi pi-bolt text-white text-xl"></i>
            </div>
            <span class="text-xl font-black text-white tracking-tighter">LANG COACH</span>
          </div>
          
          <div class="hidden md:flex items-center gap-1">
            <router-link 
              v-for="item in navItems" 
              :key="item.path"
              :to="item.path"
              class="px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
              :class="$route.path === item.path ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'"
            >
              <i :class="item.icon"></i>
              {{ item.label }}
            </router-link>
          </div>

          <div class="flex items-center gap-4">
            <button @click="toggleDarkMode" class="w-10 h-10 rounded-xl glass-panel flex items-center justify-center hover-glow">
              <i :class="isDarkMode ? 'pi pi-sun' : 'pi pi-moon'" class="text-yellow-400"></i>
            </button>
            <div class="md:hidden">
              <i class="pi pi-bars text-white text-xl"></i>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-1 relative z-10">
      <Onboarding v-if="showOnboarding" @complete="showOnboarding = false" />
      <router-view v-slot="{ Component }">
        <transition 
          enter-active-class="animate__animated animate__fadeIn animate__faster"
          leave-active-class="animate__animated animate__fadeOut animate__faster"
          mode="out-in"
        >
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Footer -->
    <footer class="py-8 text-center text-slate-500 text-xs border-t border-white/5 relative z-10">
      <p>© 2026 English+Japanese Learning Coach • Powered by AI</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';
import Onboarding from './components/Onboarding.vue';

const isDarkMode = ref(true);
const showOnboarding = ref(false);

const checkOnboarding = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/progress');
    if (res.data.success && res.data.progress.rpg_stats) {
      showOnboarding.value = !res.data.progress.rpg_stats.is_onboarded;
    }
  } catch (e) {
    console.error(e);
  }
};
const navItems = [
  { path: '/', label: '今日課程', icon: 'pi pi-calendar' },
  { path: '/progress', label: '我的進度', icon: 'pi pi-chart-bar' },
  { path: '/archive', label: '課程歸檔', icon: 'pi pi-folder-open' }
];

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value;
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark-mode');
  } else {
    document.documentElement.classList.remove('dark-mode');
  }
};

onMounted(() => {
  document.documentElement.classList.add('dark-mode');
  checkOnboarding();
});
</script>

<style>
/* 全域樣式覆寫 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background: #0f172a;
  color: #f8fafc;
  font-family: 'Inter', 'Noto Sans TC', sans-serif;
  overflow-x: hidden;
}

.router-link-active {
  position: relative;
}

.router-link-active::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  background: #3b82f6;
  border-radius: 50%;
  box-shadow: 0 0 8px #3b82f6;
}

/* 確保 PrimeVue 組件在深色模式下的樣式 */
.p-component {
  font-family: inherit;
}
</style>
