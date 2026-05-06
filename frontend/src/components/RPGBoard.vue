<template>
  <div class="panel">
    <h3>{{ t('rpgBoard.title') }}</h3>
    <p>{{ t('rpgBoard.level', { level: stats.level, title: stats.title }) }}</p>
    <p>{{ t('rpgBoard.xp', { current: stats.current_xp, next: stats.next_level_xp, total: stats.total_xp }) }}</p>
    <p>{{ t('rpgBoard.streak', { days: stats.streak_days }) }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { UserRPGStats } from '@/types'

const { t } = useI18n()
defineProps<{ stats: UserRPGStats }>()
</script>
