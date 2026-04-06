<template>
  <div 
    class="word-card-container perspective-1000 w-full h-64 cursor-pointer group"
    @click="isFlipped = !isFlipped"
  >
    <div 
      class="relative w-full h-full transition-transform duration-500 transform-style-3d"
      :class="{ 'rotate-y-180': isFlipped }"
    >
      <!-- Front Side -->
      <div 
        class="absolute inset-0 backface-hidden glass-panel rounded-2xl p-6 flex flex-col items-center justify-center text-center border-2"
        :class="rarityClass"
      >
        <div class="absolute top-3 right-3">
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/10 text-white/70 uppercase">
            {{ card.rarity }}
          </span>
        </div>
        <h3 class="text-3xl font-bold text-white mb-2">{{ card.word }}</h3>
        <p class="text-blue-400 font-mono text-sm">{{ card.phonetic || card.reading || card.reading_kana }}</p>
        <div class="mt-4 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-slate-400">
          點擊翻面查看定義
        </div>
      </div>

      <!-- Back Side -->
      <div 
        class="absolute inset-0 backface-hidden rotate-y-180 glass-panel rounded-2xl p-6 flex flex-col border-2"
        :class="rarityClass"
      >
        <div class="flex-1 overflow-y-auto">
          <h4 class="text-lg font-bold text-blue-400 mb-2">定義</h4>
          <p class="text-white text-sm mb-4">{{ card.definition }}</p>
          
          <h4 class="text-lg font-bold text-purple-400 mb-2">例句</h4>
          <p class="text-slate-300 text-xs italic">{{ card.example }}</p>
          <p class="text-slate-400 text-xs mt-1">{{ card.example_translation }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  card: any;
}>();

const isFlipped = ref(false);

const rarityClass = computed(() => {
  const r = props.card.rarity?.toUpperCase();
  if (r === 'S' || r === 'SS' || r === 'LEGENDARY') return 'border-yellow-500/50 shadow-[0_0_15px_rgba(234,179,8,0.3)]';
  if (r === 'A' || r === 'EPIC') return 'border-purple-500/50 shadow-[0_0_15px_rgba(168,85,247,0.3)]';
  if (r === 'B' || r === 'RARE') return 'border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.3)]';
  return 'border-slate-500/30';
});
</script>

<style scoped>
.perspective-1000 { perspective: 1000px; }
.transform-style-3d { transform-style: preserve-3d; }
.backface-hidden { backface-visibility: hidden; }
.rotate-y-180 { transform: rotateY(180deg); }
</style>
