<template>
  <div v-if="feynman" class="section-card" data-testid="lesson-feynman">
    <div class="section-header">
      <div>
        <h2>用自己的話解釋本課</h2>
        <p class="section-description">{{ feynman.prompt }}</p>
      </div>
    </div>
    <ul>
      <li v-for="item in feynman.checklist" :key="item">{{ item }}</li>
    </ul>
    <textarea
      v-model="draft"
      rows="5"
      placeholder="寫下你會怎麼教別人這一課..."
      data-testid="feynman-input"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FeynmanPrompt } from '@/types'

defineProps<{ feynman?: FeynmanPrompt }>()

const draft = ref('')
</script>
