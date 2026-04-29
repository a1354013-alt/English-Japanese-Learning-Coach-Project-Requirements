<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

function switchLang(lang: string) {
  locale.value = lang
  localStorage.setItem('locale', lang)
}
</script>

<template>
  <div class="language-switcher">
    <button
      :class="{ active: locale === 'zh-TW' }"
      @click="switchLang('zh-TW')"
    >
      中文
    </button>

    <span class="divider">|</span>

    <button
      :class="{ active: locale === 'en' }"
      @click="switchLang('en')"
    >
      English
    </button>
  </div>
</template>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
  gap: 6px;
}

.language-switcher button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #64748b;
}

.language-switcher button.active {
  color: #2563eb;
  font-weight: 600;
}

.divider {
  color: #cbd5f5;
}
</style>