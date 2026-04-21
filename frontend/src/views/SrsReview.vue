<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">SRS Review</h2>
      <div class="row gap-sm center">
        <select v-model="language" style="min-width: 140px">
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
        <button class="secondary" @click="load" :disabled="loading">Refresh</button>
      </div>
    </div>

    <div class="panel" v-if="loading && items.length === 0">
      <p>Loading due items...</p>
    </div>

    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">Retry</button>
    </div>

    <div class="panel" v-else-if="items.length === 0">
      <p>No due items. You're all caught up.</p>
    </div>

    <div class="panel" v-else>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">Word</th>
            <th align="left">Definition</th>
            <th align="left">Next review</th>
            <th align="left">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.language + ':' + item.word">
            <td style="font-weight: 600">{{ item.word }}</td>
            <td>{{ item.definition_zh ?? '' }}</td>
            <td>{{ new Date(item.next_review).toLocaleString('zh-TW') }}</td>
            <td class="row gap-sm">
              <button class="secondary" @click="review(item.word, 5)" :disabled="submitting">Easy</button>
              <button class="secondary" @click="review(item.word, 3)" :disabled="submitting">Hard</button>
              <button class="secondary" @click="review(item.word, 1)" :disabled="submitting">Forgot</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 0.75rem; font-size: 0.85rem; color: #666">
        Demo note: review updates your SRS schedule; XP/progress are not granted here.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { reviewApi } from '@/services/api'
import type { Language, SrsItem } from '@/types'

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
    error.value = e instanceof Error ? e.message : 'Failed to load due items'
  } finally {
    loading.value = false
  }
}

const review = async (word: string, quality: number) => {
  submitting.value = true
  try {
    await reviewApi.submitSrsReview(word, language.value, quality)
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

