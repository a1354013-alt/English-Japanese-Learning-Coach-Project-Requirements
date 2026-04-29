<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <h2 style="margin: 0">{{ t('vocabulary.title') }}</h2>
      <button class="secondary" @click="load" :disabled="loading">{{ t('common.refresh') }}</button>
    </div>

    <div class="panel grid" style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))">
      <div>
        <label>{{ t('common.language') }}</label>
        <select v-model="language">
          <option value="">{{ t('common.all') }}</option>
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
      </div>
      <div>
        <label>{{ t('vocabulary.searchLabel') }}</label>
        <input v-model="q" :placeholder="t('vocabulary.searchPlaceholder')" @keyup.enter="load" />
      </div>
      <div class="row center" style="margin-top: 1.6rem">
        <button @click="load" :disabled="loading">{{ t('common.search') }}</button>
      </div>
    </div>

    <div class="panel" v-if="loading && items.length === 0">
      <p>{{ t('vocabulary.loading') }}</p>
    </div>

    <div class="panel" v-else-if="error">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">{{ t('common.retry') }}</button>
    </div>

    <div class="panel" v-else-if="items.length === 0">
      <p>{{ t('vocabulary.empty') }}</p>
      <p style="margin: 0.35rem 0 0; color: #475569; font-size: 0.9rem">
        {{ t('vocabulary.emptyHint') }}
      </p>
    </div>

    <div class="panel" v-else>
      <p style="margin-top: 0; color: #666; font-size: 0.85rem">{{ t('vocabulary.total', { count }) }}</p>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">{{ t('common.word') }}</th>
            <th align="left">{{ t('vocabulary.reading') }}</th>
            <th align="left">{{ t('common.definition') }}</th>
            <th align="left">{{ t('common.example') }}</th>
            <th align="left">{{ t('vocabulary.action') }}</th>
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
                {{ deletingId === v.id ? t('vocabulary.deleting') : t('vocabulary.delete') }}
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
import { useI18n } from 'vue-i18n'
import { importApi } from '@/services/api'
import type { ImportedVocabularyItem, Language } from '@/types'

const { t } = useI18n()
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
    console.error(e)
    error.value = t('vocabulary.loadError')
  } finally {
    loading.value = false
  }
}

const remove = async (id: number) => {
  if (!window.confirm(t('vocabulary.deleteConfirm'))) {
    return
  }
  deletingId.value = id
  try {
    await importApi.deleteImportedVocabulary(id)
    await load()
  } catch (e) {
    console.error(e)
    error.value = t('vocabulary.deleteError')
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>
