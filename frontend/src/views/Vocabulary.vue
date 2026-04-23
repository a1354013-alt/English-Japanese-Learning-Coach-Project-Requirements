<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">Imported Vocabulary</h2>
      <button class="secondary" @click="load" :disabled="loading">Refresh</button>
    </div>

    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))">
      <div>
        <label>Language</label>
        <select v-model="language">
          <option value="">All</option>
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
      </div>
      <div>
        <label>Search</label>
        <input v-model="q" placeholder="word / definition" @keyup.enter="load" />
      </div>
      <div class="row center" style="margin-top: 1.6rem">
        <button @click="load" :disabled="loading">Search</button>
      </div>
    </div>

    <div class="panel" v-if="loading && items.length === 0">
      <p>Loading vocabulary...</p>
    </div>

    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">Retry</button>
    </div>

    <div class="panel" v-else-if="items.length === 0">
      <p>No imported vocabulary yet.</p>
      <p style="margin: 0.35rem 0 0; color: #475569; font-size: 0.9rem">
        Use the Archive page → Excel Import to add items.
      </p>
    </div>

    <div class="panel" v-else>
      <p style="margin-top: 0; color: #666; font-size: 0.85rem">Total: {{ count }}</p>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">Word</th>
            <th align="left">Reading</th>
            <th align="left">Definition</th>
            <th align="left">Example</th>
            <th align="left">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in items" :key="v.id">
            <td style="font-weight: 600">{{ v.word }}</td>
            <td>{{ v.reading ?? '' }}</td>
            <td>{{ v.definition_zh }}</td>
            <td style="max-width: 420px">
              <div>{{ v.example_sentence ?? '' }}</div>
              <div style="color: #666; font-size: 0.85rem">{{ v.example_translation ?? '' }}</div>
            </td>
            <td>
              <button class="secondary" @click="remove(v.id)" :disabled="deletingId === v.id">
                {{ deletingId === v.id ? 'Deleting...' : 'Delete' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { importApi } from '@/services/api'
import type { ImportedVocabularyItem, Language } from '@/types'

const language = ref<'' | Language>('')
const q = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const items = ref<ImportedVocabularyItem[]>([])
const count = ref(0)
const deletingId = ref<number | null>(null)

const load = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await importApi.listImportedVocabulary({
      language: language.value || undefined,
      q: q.value || undefined,
      limit: 200,
      offset: 0,
    })
    items.value = res.items
    count.value = res.count
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load vocabulary'
  } finally {
    loading.value = false
  }
}

const remove = async (id: number) => {
  if (!window.confirm('Delete this imported vocabulary item? This also removes its derived SRS entry and any matching word card.')) {
    return
  }
  deletingId.value = id
  try {
    await importApi.deleteImportedVocabulary(id)
    await load()
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>

