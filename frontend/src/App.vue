<template>
  <div class="app-shell">
    <div class="notice-stack" aria-live="polite">
      <div
        v-for="notice in notices"
        :key="notice.id"
        :class="['app-notice', `tone-${notice.tone}`]"
        role="status"
      >
        <span>{{ notice.message }}</span>
        <button
          type="button"
          class="secondary"
          @click="dismissNotice(notice.id)"
        >
          {{ t('common.dismiss') }}
        </button>
      </div>
    </div>

    <div
      v-if="apiErrorMessage"
      class="api-error-banner row between center"
      role="alert"
    >
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

    <div
      v-if="confirmState.open"
      class="feedback-overlay"
      role="dialog"
      aria-modal="true"
      data-testid="app-confirm-dialog"
    >
      <div class="feedback-dialog panel">
        <h2>{{ confirmState.title }}</h2>
        <p>{{ confirmState.message }}</p>
        <div class="row gap-sm">
          <button
            type="button"
            class="secondary"
            data-testid="app-confirm-cancel"
            @click="resolveConfirmation(false)"
          >
            {{ confirmState.cancelLabel }}
          </button>
          <button
            type="button"
            data-testid="app-confirm-accept"
            @click="resolveConfirmation(true)"
          >
            {{ confirmState.confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Onboarding from '@/components/Onboarding.vue'
import {
  confirmState,
  dismissNotice,
  notices,
  resolveConfirmation,
} from '@/services/appFeedback'
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

.notice-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 60;
  display: grid;
  gap: 10px;
  width: min(360px, calc(100vw - 32px));
}

.app-notice {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid #cbd5e1;
  background: #fff;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
}

.app-notice.tone-success {
  border-color: #86efac;
  background: #f0fdf4;
  color: #166534;
}

.app-notice.tone-warning {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #92400e;
}

.app-notice.tone-error {
  border-color: #fecaca;
  background: #fef2f2;
  color: #991b1b;
}

.app-notice.tone-info {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.feedback-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.58);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 55;
}

.feedback-dialog {
  width: min(460px, 100%);
}

.feedback-dialog h2 {
  margin-top: 0;
}

.feedback-dialog p {
  margin: 0 0 16px;
  color: #475569;
}

@media (max-width: 760px) {
  .language-switcher {
    margin-left: 0;
  }

  .notice-stack {
    top: auto;
    bottom: 16px;
    left: 16px;
    right: 16px;
    width: auto;
  }
}
</style>
