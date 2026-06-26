<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <h2 style="margin: 0">{{ t('materials.title') }}</h2>
      <div class="row gap-sm center">
        <select v-model="selectedLanguage" style="min-width: 140px">
          <option value="">{{ t('common.all') }}</option>
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
        <button class="secondary" :disabled="loading" @click="load">
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top: 0">{{ t('materials.upload') }}</h3>
      <p style="font-size: 0.85rem; color: #666">
        {{ t('materials.supported') }}
      </p>
      <input
        type="file"
        accept=".txt,.md,.csv,.pdf"
        :disabled="!language"
        @change="handleUpload"
      />
      <p v-if="!language" style="font-size: 0.75rem; color: #d32f2f">
        {{ t('materials.selectLanguageBeforeUpload') }}
      </p>
    </div>

    <LoadingState
      v-if="loading && materials.length === 0"
      panel-class="panel"
      :message="t('materials.loading')"
    />

    <ErrorState
      v-else-if="error"
      panel-class="panel"
      :message="error"
      :retry-label="t('common.retry')"
      @retry="load"
    />

    <EmptyState
      v-else-if="materials.length === 0"
      panel-class="panel"
      :message="t('materials.empty')"
    />

    <div v-else class="panel">
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
            <td>{{ m.title || m.source }}</td>
            <td>{{ m.language }}</td>
            <td>
              {{
                m.uploaded_at ? new Date(m.uploaded_at).toLocaleString() : ''
              }}
            </td>
            <td>{{ m.total_chunks ?? '' }}</td>
            <td>
              <button
                class="secondary"
                :disabled="deletingId === m.doc_id"
                @click="remove(m.doc_id)"
              >
                {{ t('materials.delete') }}
              </button>
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
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import EmptyState from '@/components/state/EmptyState.vue'
import ErrorState from '@/components/state/ErrorState.vue'
import LoadingState from '@/components/state/LoadingState.vue'
import { importApi } from '@/services/api'
import { requestConfirmation, showNotice } from '@/services/appFeedback'
import type { Language, RagMaterial } from '@/types'
import { formatApiErrorDetail } from '@/utils/apiErrorDetail'

const props = withDefaults(
  defineProps<{ embedded?: boolean; language?: Language }>(),
  {
    embedded: false,
    language: undefined,
  },
)

const { t } = useI18n()
const selectedLanguage = ref<'' | Language>('')
const language = computed<'' | Language>(
  () => props.language ?? selectedLanguage.value,
)
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
    error.value = axios.isAxiosError(e)
      ? formatApiErrorDetail(e.response?.data)
      : t('materials.loadError')
  } finally {
    loading.value = false
  }
}

const handleUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!language.value) {
    showNotice(t('materials.selectLanguageBeforeUpload'), 'warning')
    ;(event.target as HTMLInputElement).value = ''
    return
  }
  try {
    await importApi.uploadRagMaterial(language.value, file)
    await load()
  } catch (e) {
    console.error(e)
    error.value = axios.isAxiosError(e)
      ? formatApiErrorDetail(e.response?.data)
      : t('materials.uploadError')
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

const remove = async (docId: string) => {
  const confirmed = await requestConfirmation({
    title: t('materials.confirmDeleteTitle'),
    message: t('materials.confirmDeleteMessage'),
    confirmLabel: t('common.delete'),
    cancelLabel: t('common.cancel'),
  })
  if (!confirmed) return

  deletingId.value = docId
  try {
    await importApi.deleteRagMaterial(docId)
    await load()
  } catch (e) {
    console.error(e)
    error.value = axios.isAxiosError(e)
      ? formatApiErrorDetail(e.response?.data)
      : t('materials.deleteError')
  } finally {
    deletingId.value = null
  }
}

onMounted(load)

watch(
  () => props.language,
  () => {
    if (props.embedded) {
      void load()
    }
  },
)
</script>
