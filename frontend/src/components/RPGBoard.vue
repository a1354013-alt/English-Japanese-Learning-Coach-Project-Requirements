<template>
  <div class="panel">
    <h3>RPG Summary</h3>
    <p>Level {{ stats.level }} - {{ stats.title }}</p>
    <p>XP {{ stats.current_xp }} / {{ stats.next_level_xp }} (Total {{ stats.total_xp }})</p>
    <p>Streak {{ stats.streak_days }} days</p>
  </div>
</template>

<script setup lang="ts">
import type { UserRPGStats } from '@/types'

defineProps<{ stats: UserRPGStats }>()
</script>
