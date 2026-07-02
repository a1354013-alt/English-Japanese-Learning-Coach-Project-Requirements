<template>
  <div v-if="reviewPlan" class="section-card" data-testid="lesson-review-plan">
    <div class="section-header">
      <div>
        <h2>複習計畫</h2>
        <p class="section-description">把今天的課拆成間隔複習節點。</p>
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
import type { ReviewPlan } from '@/types'

const props = defineProps<{ reviewPlan?: ReviewPlan }>()

const groups = computed(() => [
  { label: 'Today', items: props.reviewPlan?.today ?? [] },
  { label: '+1 day', items: props.reviewPlan?.next_1_day ?? [] },
  { label: '+3 days', items: props.reviewPlan?.next_3_days ?? [] },
  { label: '+7 days', items: props.reviewPlan?.next_7_days ?? [] },
])
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
