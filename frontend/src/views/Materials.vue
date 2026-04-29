<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <h2 style="margin: 0">{{ t('materials.title') }}</h2>
      <div class="row gap-sm center">
        <select v-model="language" style="min-width: 140px">
          <option value="">{{ t('common.all') }}</option>
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
        <button class="secondary" @click="load" :disabled="loading">{{ t('common.refresh') }}</button>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top: 0">{{ t('materials.upload') }}</h3>
      <p style="font-size: 0.85rem; color: #666">{{ t('materials.supported') }}</p>
      <input type="file" accept=".txt,.md,.csv" @change="handleUpload" :disabled="!language" />
      <p v-if="!language" style="font-size: 0.75rem; color: #d32f2f">
        {{ t('materials.selectLanguageBeforeUpload') }}
      </p>
    </div>

    <div class="panel" v-if="loading && materials.length === 0">
      <p>{{ t('materials.loading') }}</p>
    </div>

    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">{{ t('common.retry') }}</button>
    </div>

    <div class="panel" v-else-if="materials.length === 0">
      <p>{{ t('materials.empty') }}</p>
    </div>

    <div class="panel" v-else>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">{{ t('materials.source') }}</th>
            <th align="left">{{ t('common.language') }}</th>
            <th align="left">{{ t('common.uploaded') }}</th>
            <th align="left">{{ t('materials.chunks') }}</th>
            <th align="left">{{ t('common.action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in materials" :key="m.doc_id">
            <td>{{ m.source }}</td>
            <td>{{ m.language }}</td>
            <td>{{ m.uploaded_at ? new Date(m.uploaded_at).toLocaleString() : '' }}</td>
            <td>{{ m.total_chunks ?? '' }}</td>
            <td>
              <button class="secondary" @click="remove(m.doc_id)" :disabled="deletingId === m.doc_id">{{ t('materials.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 0.75rem; font-size: 0.85rem; color: #666">
        {{ t('materials.demoNote') }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { importApi } from '@/services/api'
import type { Language, RagMaterial } from '@/types'

withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
})

const { t } = useI18n()
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
    console.error(e)
    error.value = t('materials.loadError')
  } finally {
    loading.value = false
  }
}

const handleUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!language.value) {
    window.alert(t('materials.selectLanguageBeforeUpload'))
    ;(event.target as HTMLInputElement).value = ''
    return
  }
  try {
    await importApi.uploadRagMaterial(language.value, file)
    await load()
  } catch (e) {
    console.error(e)
    error.value = t('materials.uploadError')
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

const remove = async (docId: string) => {
  deletingId.value = docId
  try {
    await importApi.deleteRagMaterial(docId)
    await load()
  } catch (e) {
    console.error(e)
    error.value = t('materials.deleteError')
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>
