<template>
  <div class="app-shell">
    <div v-if="apiErrorMessage" class="api-error-banner row between center" role="alert">
      <span>{{ apiErrorMessage }}</span>
      <button type="button" class="secondary" @click="clearApiError">
        {{ t('common.dismiss') }}
      </button>
    </div>

    <header class="topbar">
      <div class="container row between center">
        <h1 class="brand" data-testid="app-title" @click="$router.push('/')">
          {{ t('app.title') }}
        </h1>

        <nav class="topnav">
          <RouterLink to="/">{{ t('nav.today') }}</RouterLink>
          <RouterLink to="/workspace">{{ t('nav.workspace') }}</RouterLink>
          <RouterLink to="/progress" data-testid="nav-progress">
            {{ t('nav.progress') }}
          </RouterLink>
          <RouterLink to="/analytics">{{ t('nav.analytics') }}</RouterLink>
        </nav>

        <div class="language-switcher" :aria-label="t('common.language')">
          <button
            type="button"
            :class="{ active: locale === 'zh-TW' }"
            @click="switchLanguage('zh-TW')"
          >
            {{ t('language.zh') }}
          </button>
          <span>|</span>
          <button
            type="button"
            :class="{ active: locale === 'en' }"
            @click="switchLanguage('en')"
          >
            {{ t('language.en') }}
          </button>
        </div>
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
import { useI18n } from 'vue-i18n'
import Onboarding from '@/components/Onboarding.vue'
import { apiErrorMessage, clearApiError } from '@/services/apiNotifications'
import { progressApi } from '@/services/api'

const showOnboarding = ref(false)
const { t, locale } = useI18n()

function switchLanguage(lang: 'zh-TW' | 'en') {
  locale.value = lang
  localStorage.setItem('locale', lang)
}

onMounted(async () => {
  try {
    const { progress } = await progressApi.getProgress()
    showOnboarding.value = !progress.rpg_stats.is_onboarded
  } catch {
    showOnboarding.value = false
  }
})
</script>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  font-size: 14px;
}

.language-switcher button {
  border: 0;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-weight: 500;
  padding: 6px 4px;
}

.language-switcher button.active {
  color: #2563eb;
  font-weight: 700;
}

.language-switcher span {
  color: #cbd5e1;
}

@media (max-width: 760px) {
  .language-switcher {
    margin-left: 0;
  }
}
</style>
