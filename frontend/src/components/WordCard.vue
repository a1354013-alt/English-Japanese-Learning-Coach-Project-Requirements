<template>
  <div class="panel">
    <strong>{{ card.word }}</strong>
    <div>{{ card.definition_zh || 'No definition' }}</div>
    <small>{{ card.example_sentence || '' }}</small>
    <div>Rarity: {{ card.rarity }}</div>
  </div>
</template>

<script setup lang="ts">
import type { WordCard } from '@/types'

defineProps<{ card: WordCard }>()
</script>
