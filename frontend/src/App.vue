<template>
  <div class="app-shell">
    <div v-if="apiErrorMessage" class="api-error-banner row between center" role="alert">
      <span>{{ apiErrorMessage }}</span>
      <button type="button" class="secondary" @click="clearApiError">Dismiss</button>
    </div>

    <header class="topbar">
      <div class="container row between center">
        <h1 class="brand" data-testid="app-title" @click="$router.push('/')">English-Japanese Learning Coach</h1>
        <nav class="row gap-sm">
          <RouterLink to="/">Today</RouterLink>
          <RouterLink to="/review">Review</RouterLink>
          <RouterLink to="/archive">Archive</RouterLink>
          <RouterLink to="/materials">Materials</RouterLink>
          <RouterLink to="/vocabulary">Vocabulary</RouterLink>
          <RouterLink to="/mistakes">Mistakes</RouterLink>
          <RouterLink to="/progress" data-testid="nav-progress">Progress</RouterLink>
          <RouterLink to="/writing">Writing</RouterLink>
          <RouterLink to="/chat">Chat (Preview)</RouterLink>
          <RouterLink to="/analytics">Analytics</RouterLink>
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
import { apiErrorMessage, clearApiError } from '@/services/apiNotifications'
import { progressApi } from '@/services/api'

const showOnboarding = ref(false)

onMounted(async () => {
  try {
    const { progress } = await progressApi.getProgress()
    showOnboarding.value = !progress.rpg_stats.is_onboarded
  } catch {
    showOnboarding.value = false
  }
})
</script>
