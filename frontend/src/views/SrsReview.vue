<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <h2 style="margin: 0">{{ t('review.title') }}</h2>
      <div class="row gap-sm center">
        <select v-model="language" style="min-width: 140px">
          <option value="EN">{{ t('common.english') }}</option>
          <option value="JP">{{ t('common.japanese') }}</option>
        </select>
        <select v-model="itemType" style="min-width: 160px">
          <option value="all">{{ t('common.all') }}</option>
          <option value="vocabulary">{{ t('review.vocabulary') }}</option>
          <option value="grammar">{{ t('review.grammar') }}</option>
          <option value="sentence_pattern">
            {{ t('review.sentencePatterns') }}
          </option>
        </select>
        <button class="secondary" :disabled="loading" @click="load">
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <div v-if="loading && items.length === 0" class="panel">
      <p>{{ t('review.loading') }}</p>
    </div>

    <div v-else-if="error" class="panel">
      <p style="color: #d32f2f">{{ error }}</p>
      <button class="secondary" @click="load">{{ t('common.retry') }}</button>
    </div>

    <div v-else-if="items.length === 0" class="panel">
      <p>{{ t('review.empty') }}</p>
    </div>

    <div v-else class="panel">
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr>
            <th align="left">{{ t('common.word') }}</th>
            <th align="left">{{ t('common.definition') }}</th>
            <th align="left">{{ t('review.metadata') }}</th>
            <th align="left">{{ t('review.nextReview') }}</th>
            <th align="left">{{ t('common.action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in items"
            :key="item.item_id"
            data-testid="srs-review-row"
          >
            <td style="font-weight: 600">
              <div>{{ item.item_key }}</div>
              <small class="muted">
                {{ formatItemTypeLabel(item.item_type) }} /
                {{ formatMasteryStateLabel(item.mastery_state) }}
              </small>
            </td>
            <td>
              <div>{{ formatDefinition(item) }}</div>
              <small v-if="item.memory_tip" class="muted">
                {{ item.memory_tip }}
              </small>
            </td>
            <td>
              <div>{{ item.category ?? '-' }}</div>
              <small v-if="item.root" class="muted"
                >root: {{ item.root }}</small
              >
              <small v-if="item.tags.length" class="muted">
                tags: {{ item.tags.join(', ') }}
              </small>
            </td>
            <td>{{ formatNextReview(item.due_at) }}</td>
            <td class="row gap-sm wrap">
              <button
                class="secondary"
                :disabled="submitting"
                @click="review(item, 0, false)"
              >
                {{ t('review.forgot') }}
              </button>
              <button
                class="secondary"
                :disabled="submitting"
                @click="review(item, 3, false)"
              >
                {{ t('review.hard') }}
              </button>
              <button
                class="secondary"
                :disabled="submitting"
                @click="review(item, 4, true)"
              >
                {{ t('review.good') }}
              </button>
              <button
                class="secondary"
                :disabled="submitting"
                @click="review(item, 5, true)"
              >
                {{ t('review.easy') }}
              </button>
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
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { reviewApi } from '@/services/api'
import type { Language, LearningItemDue, LearningItemType } from '@/types'

withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
})

const { t } = useI18n()
const language = ref<Language>('EN')
const itemType = ref<LearningItemType | 'all'>('all')
const items = ref<LearningItemDue[]>([])
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)

const formatNextReview = (value: string | null) =>
  value ? new Date(value).toLocaleString() : '-'

const formatDefinition = (item: LearningItemDue) => {
  const content = item.content ?? {}
  if (typeof content.definition_zh === 'string' && content.definition_zh) {
    return content.definition_zh
  }
  if (typeof content.explanation === 'string' && content.explanation) {
    return content.explanation
  }
  if (typeof content.meaning_zh === 'string' && content.meaning_zh) {
    return content.meaning_zh
  }
  return ''
}

const formatItemTypeLabel = (value: LearningItemType) =>
  t(`review.itemTypeLabels.${value}`)

const formatMasteryStateLabel = (value: LearningItemDue['mastery_state']) =>
  t(`review.masteryStateLabels.${value}`)

const load = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await reviewApi.getDueLearningItems({
      language: language.value,
      item_type: itemType.value === 'all' ? undefined : itemType.value,
    })
    items.value = res.items
  } catch (e) {
    console.error(e)
    error.value = t('review.loadError')
  } finally {
    loading.value = false
  }
}

const review = async (
  item: LearningItemDue,
  rating: number,
  correct: boolean,
) => {
  submitting.value = true
  try {
    await reviewApi.submitLearningItemReview({
      item_id: item.item_id,
      rating,
      correct,
      source: 'srs_review',
    })
    await load()
  } catch (e) {
    console.error(e)
    error.value = t('review.submitError')
  } finally {
    submitting.value = false
  }
}

watch([language, itemType], () => {
  void load()
})

onMounted(load)
</script>

<style scoped>
.muted {
  display: block;
  color: #64748b;
  margin-top: 4px;
}

.wrap {
  flex-wrap: wrap;
}
</style>
