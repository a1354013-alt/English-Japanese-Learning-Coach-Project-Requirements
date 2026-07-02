<template>
  <div v-if="hasContent" class="section-card" data-testid="lesson-immersion">
    <div class="section-header">
      <div>
        <h2>沉浸跟讀</h2>
        <p class="section-description">文字版 shadowing，先練節奏與分段。</p>
      </div>
    </div>
    <div class="immersion-grid">
      <section>
        <h3>Shadowing</h3>
        <p v-for="(line, index) in safeImmersion.shadowing_text" :key="index">
          <strong>{{ line.speaker }}:</strong> {{ line.text }}
          <small>{{ line.translation }}</small>
        </p>
      </section>
      <section>
        <h3>Repeat Chunks</h3>
        <ul>
          <li v-for="chunk in safeImmersion.repeat_chunks" :key="chunk">
            {{ chunk }}
          </li>
        </ul>
      </section>
      <section>
        <h3>Listening Tips</h3>
        <ul>
          <li v-for="tip in safeImmersion.listening_tips" :key="tip">
            {{ tip }}
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ImmersionSection } from '@/types'

const props = defineProps<{ immersion?: ImmersionSection }>()

const safeImmersion = computed<ImmersionSection>(() => ({
  shadowing_text: props.immersion?.shadowing_text ?? [],
  repeat_chunks: props.immersion?.repeat_chunks ?? [],
  listening_tips: props.immersion?.listening_tips ?? [],
}))

const hasContent = computed(
  () =>
    safeImmersion.value.shadowing_text.length > 0 ||
    safeImmersion.value.repeat_chunks.length > 0 ||
    safeImmersion.value.listening_tips.length > 0,
)
</script>

<style scoped>
.immersion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.immersion-grid section {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.immersion-grid h3,
.immersion-grid p {
  margin: 0;
}

.immersion-grid p,
.immersion-grid ul {
  margin-top: 8px;
}

.immersion-grid small {
  display: block;
  color: #64748b;
}
</style>
