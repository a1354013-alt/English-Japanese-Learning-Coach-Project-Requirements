<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="container row between center">
        <h1 class="brand" @click="$router.push('/')">English-Japanese Learning Coach</h1>
        <nav class="row gap-sm">
          <RouterLink to="/">Today</RouterLink>
          <RouterLink to="/archive">Archive</RouterLink>
          <RouterLink to="/progress">Progress</RouterLink>
          <RouterLink to="/writing">Writing</RouterLink>
        </nav>
      </div>
    </header>

    <main class="container">
      <Onboarding v-if="showOnboarding" @complete="showOnboarding = false" />
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Onboarding from '@/components/Onboarding.vue'
import { progressApi } from '@/services/api'

const showOnboarding = ref(false)

onMounted(async () => {
  const { progress } = await progressApi.getProgress()
  showOnboarding.value = !progress.rpg_stats.is_onboarded
})
</script>
