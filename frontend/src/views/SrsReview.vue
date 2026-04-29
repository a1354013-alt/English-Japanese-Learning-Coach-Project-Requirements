<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <h2 style="margin: 0">{{ t('review.title') }}</h2>
      <div class="row gap-sm center">
        <select v-model="language" style="min-width: 140px">
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
        <button class="secondary" @click="load" :disabled="loading">{{ t('common.refresh') }}</button>
      </div>
    </div>

    <div class="panel" v-if="loading && items.length === 0">
      <p>{{ t('review.loading') }}</p>
    </div>

    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">{{ t('common.retry') }}</button>
    </div>

    <div class="panel" v-else-if="items.length === 0">
      <p>{{ t('review.empty') }}</p>
    </div>

    <div class="panel" v-else>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">{{ t('common.word') }}</th>
            <th align="left">{{ t('common.definition') }}</th>
            <th align="left">{{ t('review.nextReview') }}</th>
            <th align="left">{{ t('common.action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.language + ':' + item.word">
            <td style="font-weight: 600">{{ item.word }}</td>
            <td>{{ item.definition_zh ?? '' }}</td>
            <td>{{ new Date(item.next_review).toLocaleString() }}</td>
            <td class="row gap-sm">
              <button class="secondary" @click="review(item.word, 5)" :disabled="submitting">{{ t('review.easy') }}</button>
              <button class="secondary" @click="review(item.word, 3)" :disabled="submitting">{{ t('review.hard') }}</button>
              <button class="secondary" @click="review(item.word, 1)" :disabled="submitting">{{ t('review.forgot') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 0.75rem; font-size: 0.85rem; color: #666">
        {{ t('review.demoNote') }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { reviewApi } from '@/services/api'
import type { Language, SrsItem } from '@/types'

withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
})

const { t } = useI18n()
const language = ref<Language>('EN')
const items = ref<SrsItem[]>([])
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)

const load = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await reviewApi.getDueSrs(language.value)
    items.value = res.items
  } catch (e) {
    console.error(e)
    error.value = t('review.loadError')
  } finally {
    loading.value = false
  }
}

const review = async (word: string, quality: number) => {
  submitting.value = true
  try {
    await reviewApi.submitSrsReview(word, language.value, quality)
    await load()
  } catch (e) {
    console.error(e)
    error.value = t('review.submitError')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>
