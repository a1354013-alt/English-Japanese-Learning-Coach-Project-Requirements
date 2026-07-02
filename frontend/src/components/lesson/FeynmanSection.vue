<template>
  <div v-if="hasContent" class="section-card" data-testid="lesson-feynman">
    <div class="section-header">
      <div>
        <h2>{{ t('lessonSections.feynman.title') }}</h2>
        <p v-if="safeFeynman.prompt" class="section-description">
          {{ safeFeynman.prompt }}
        </p>
      </div>
    </div>
    <ul v-if="safeFeynman.checklist.length">
      <li v-for="item in safeFeynman.checklist" :key="item">{{ item }}</li>
    </ul>
    <textarea
      v-model="draft"
      rows="5"
      :placeholder="t('lessonSections.feynman.placeholder')"
      data-testid="feynman-input"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FeynmanPrompt } from '@/types'

const props = defineProps<{ feynman?: FeynmanPrompt }>()
const { t } = useI18n()

const draft = ref('')
const safeFeynman = computed<FeynmanPrompt>(() => ({
  prompt: props.feynman?.prompt ?? '',
  checklist: props.feynman?.checklist ?? [],
}))
const hasContent = computed(
  () =>
    safeFeynman.value.prompt.length > 0 ||
    safeFeynman.value.checklist.length > 0,
)
</script>
