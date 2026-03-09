<template>
  <div class="glass-panel rounded-2xl p-6 mb-8 relative overflow-hidden animate__animated animate__fadeInDown">
    <!-- 背景裝飾 -->
    <div class="absolute -top-10 -right-10 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl"></div>
    
    <div class="flex flex-col md:flex-row items-center gap-8 relative z-10">
      <!-- Avatar Section -->
      <div class="relative group">
        <div class="w-24 h-24 rounded-full p-1 bg-gradient-to-tr from-blue-500 via-purple-500 to-pink-500 animate-spin-slow">
          <div class="w-full h-full rounded-full bg-slate-900 flex items-center justify-center overflow-hidden">
            <img v-if="stats.avatar_url" :src="stats.avatar_url" class="w-full h-full object-cover" />
            <i v-else class="pi pi-user text-4xl text-blue-400"></i>
          </div>
        </div>
        <div class="absolute -bottom-2 -right-2 bg-yellow-500 text-slate-900 text-xs font-bold px-2 py-1 rounded-full shadow-lg">
          Lv. {{ stats.level }}
        </div>
      </div>

      <!-- Stats Section -->
      <div class="flex-1 w-full">
        <div class="flex justify-between items-end mb-2">
          <div>
            <h2 class="text-2xl font-bold text-white flex items-center gap-2">
              {{ stats.title || '冒險者' }}
              <span class="text-sm font-normal text-slate-400">#{{ stats.id || '001' }}</span>
            </h2>
            <p class="text-slate-400 text-sm">目標：{{ stats.target_exam || 'TOEIC' }} {{ stats.target_level || '700' }}</p>
          </div>
          <div class="text-right">
            <span class="text-sm text-blue-400 font-mono">{{ stats.current_xp || stats.xp }} / {{ stats.next_level_xp || (stats.level * 1000) }} XP</span>
          </div>
        </div>
        
        <!-- XP Bar -->
        <div class="h-4 w-full bg-slate-800/50 rounded-full overflow-hidden border border-white/5">
          <div 
            class="h-full xp-bar-fill transition-all duration-1000 ease-out"
            :style="{ width: `${((stats.current_xp || stats.xp) / (stats.next_level_xp || (stats.level * 1000))) * 100}%` }"
          ></div>
        </div>
      </div>

      <!-- Streak & Badges -->
      <div class="flex gap-4">
        <div class="glass-panel p-3 rounded-xl text-center min-w-[80px] hover-glow">
          <i class="pi pi-bolt text-orange-500 text-xl mb-1"></i>
          <div class="text-lg font-bold text-white">{{ stats.streak_days }}</div>
          <div class="text-[10px] text-slate-400 uppercase tracking-wider">Streak</div>
        </div>
        <div class="glass-panel p-3 rounded-xl text-center min-w-[80px] hover-glow">
          <i class="pi pi-star-fill text-yellow-500 text-xl mb-1"></i>
          <div class="text-lg font-bold text-white">{{ stats.total_lessons_completed || 0 }}</div>
          <div class="text-[10px] text-slate-400 uppercase tracking-wider">Lessons</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  stats: any;
}>();
</script>

<style scoped>
.animate-spin-slow {
  animation: spin 8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
