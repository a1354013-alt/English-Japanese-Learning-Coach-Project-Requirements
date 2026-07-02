<template>
  <div v-if="hasContent" class="section-card" data-testid="lesson-review-plan">
    <div class="section-header">
      <div>
        <h2>{{ t('lessonSections.reviewPlan.title') }}</h2>
        <p class="section-description">
          {{ t('lessonSections.reviewPlan.description') }}
        </p>
      </div>
    </div>
    <div class="plan-grid">
      <section v-for="group in groups" :key="group.label">
        <h3>{{ group.label }}</h3>
        <ul>
          <li v-for="item in group.items" :key="item">{{ item }}</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ReviewPlan } from '@/types'

const props = defineProps<{ reviewPlan?: ReviewPlan }>()
const { t } = useI18n()

const groups = computed(() => [
  {
    label: t('lessonSections.reviewPlan.today'),
    items: props.reviewPlan?.today ?? [],
  },
  {
    label: t('lessonSections.reviewPlan.next1Day'),
    items: props.reviewPlan?.next_1_day ?? [],
  },
  {
    label: t('lessonSections.reviewPlan.next3Days'),
    items: props.reviewPlan?.next_3_days ?? [],
  },
  {
    label: t('lessonSections.reviewPlan.next7Days'),
    items: props.reviewPlan?.next_7_days ?? [],
  },
])
const hasContent = computed(() =>
  groups.value.some((group) => group.items.length),
)
</script>

<style scoped>
.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.plan-grid section {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.plan-grid h3 {
  margin: 0;
}
</style>
