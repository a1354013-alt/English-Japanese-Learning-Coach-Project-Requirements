<template>
  <div class="panel">
    <strong>{{ card.word }}</strong>
    <div>{{ card.definition_zh || t('progressCenter.noDefinition') }}</div>
    <small>{{ card.example_sentence || '' }}</small>
    <div>{{ t('wordCard.rarity', { rarity: card.rarity }) }}</div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { WordCard } from '@/types'

const { t } = useI18n()
defineProps<{ card: WordCard }>()
</script>
