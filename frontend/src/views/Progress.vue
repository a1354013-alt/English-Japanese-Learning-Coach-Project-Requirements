<template>
  <section class="grid" style="margin-top: 1rem" v-if="progress">
    <RPGBoard :stats="progress.rpg_stats" />

    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))">
      <div class="panel">
        <h3>English</h3>
        <p>Current level: {{ progress.english_progress.current_level }}</p>
        <p>Completed lessons: {{ progress.english_progress.completed_lessons }}</p>
        <p>Accuracy: {{ progress.english_progress.accuracy_rate.toFixed(1) }}%</p>
      </div>
      <div class="panel">
        <h3>Japanese</h3>
        <p>Current level: {{ progress.japanese_progress.current_level }}</p>
        <p>Completed lessons: {{ progress.japanese_progress.completed_lessons }}</p>
        <p>Accuracy: {{ progress.japanese_progress.accuracy_rate.toFixed(1) }}%</p>
      </div>
    </div>

    <section class="panel">
      <h3>Collected Word Cards</h3>
      <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))">
        <WordCard v-for="card in progress.rpg_stats.word_cards" :key="`${card.language}-${card.word}`" :card="card" />
      </div>
      <p v-if="progress.rpg_stats.word_cards.length === 0">No cards yet.</p>
    </section>

    <StudyBlueprint :language="preferredLanguage" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import RPGBoard from '@/components/RPGBoard.vue'
import StudyBlueprint from '@/components/StudyBlueprint.vue'
import WordCard from '@/components/WordCard.vue'
import { progressApi } from '@/services/api'
import type { Language, UserProgress } from '@/types'

const progress = ref<UserProgress | null>(null)

const preferredLanguage = computed<Language>(() => {
  if (!progress.value) return 'EN'
  return progress.value.english_progress.accuracy_rate >= progress.value.japanese_progress.accuracy_rate ? 'EN' : 'JP'
})

onMounted(async () => {
  const response = await progressApi.getProgress()
  progress.value = response.progress
})
</script>
