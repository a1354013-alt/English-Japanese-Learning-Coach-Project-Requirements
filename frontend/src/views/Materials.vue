<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">RAG Materials</h2>
      <div class="row gap-sm center">
        <select v-model="language" style="min-width: 140px">
          <option value="">All</option>
          <option value="EN">English</option>
          <option value="JP">Japanese</option>
        </select>
        <button class="secondary" @click="load" :disabled="loading">Refresh</button>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top: 0">Upload</h3>
      <p style="font-size: 0.85rem; color: #666">Supported: .txt, .md, .csv (choose language)</p>
      <input type="file" accept=".txt,.md,.csv" @change="handleUpload" :disabled="!language" />
      <p v-if="!language" style="font-size: 0.75rem; color: #d32f2f">
        Please select a language (not "All") before uploading.
      </p>
    </div>

    <div class="panel" v-if="loading && materials.length === 0">
      <p>Loading materials...</p>
    </div>

    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">Retry</button>
    </div>

    <div class="panel" v-else-if="materials.length === 0">
      <p>No materials yet.</p>
    </div>

    <div class="panel" v-else>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">Source</th>
            <th align="left">Language</th>
            <th align="left">Uploaded</th>
            <th align="left">Chunks</th>
            <th align="left">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in materials" :key="m.doc_id">
            <td>{{ m.source }}</td>
            <td>{{ m.language }}</td>
            <td>{{ m.uploaded_at ? new Date(m.uploaded_at).toLocaleString() : '' }}</td>
            <td>{{ m.total_chunks ?? '' }}</td>
            <td>
              <button class="secondary" @click="remove(m.doc_id)" :disabled="deletingId === m.doc_id">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 0.75rem; font-size: 0.85rem; color: #666">
        Demo note: if RAG is disabled on the backend, upload/delete will return an error.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { importApi } from '@/services/api'
import type { Language, RagMaterial } from '@/types'

const language = ref<'' | Language>('')
const materials = ref<RagMaterial[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const deletingId = ref<string | null>(null)

const load = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await importApi.listRagMaterials(language.value || undefined)
    materials.value = res.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load materials'
  } finally {
    loading.value = false
  }
}

const handleUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!language.value) {
    window.alert('Please select a specific language (English or Japanese). "All" cannot be used for uploads.')
    ;(event.target as HTMLInputElement).value = ''
    return
  }
  try {
    await importApi.uploadRagMaterial(language.value, file)
    await load()
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

const remove = async (docId: string) => {
  deletingId.value = docId
  try {
    await importApi.deleteRagMaterial(docId)
    await load()
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>

