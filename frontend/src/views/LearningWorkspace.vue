<template>
  <section class="page-shell page-stack">
    <div class="hero-card">
      <div class="page-header">
        <div>
          <span class="page-eyebrow">{{ t('workspace.eyebrow') }}</span>
          <h1 class="page-title">{{ t('workspace.title') }}</h1>
          <p class="page-subtitle">
            {{ t('workspace.subtitle') }}
          </p>
        </div>
      </div>

      <div class="tab-list">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="tab-button"
          :class="{ active: currentTab === tab.key }"
          @click="setTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="section-card">
      <div class="section-header">
        <div>
          <h2>{{ currentTabMeta.label }}</h2>
          <p class="section-description">{{ currentTabMeta.description }}</p>
        </div>
      </div>

      <div class="embedded-view">
        <Materials v-if="currentTab === 'materials'" embedded />
        <WritingCenter v-else-if="currentTab === 'writing'" embedded />
        <ChatTutor v-else embedded />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import ChatTutor from '@/views/ChatTutor.vue'
import Materials from '@/views/Materials.vue'
import WritingCenter from '@/views/WritingCenter.vue'

type WorkspaceTab = 'materials' | 'writing' | 'chat'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const tabs = computed(() => [
  {
    key: 'materials' as const,
    label: t('workspace.tabs.materials'),
    description: t('workspace.descriptions.materials'),
  },
  {
    key: 'writing' as const,
    label: t('workspace.tabs.writing'),
    description: t('workspace.descriptions.writing'),
  },
  {
    key: 'chat' as const,
    label: t('workspace.tabs.chat'),
    description: t('workspace.descriptions.chat'),
  },
])

const currentTab = computed<WorkspaceTab>(() => {
  const tab = route.query.tab
  if (tab === 'writing' || tab === 'chat' || tab === 'materials') {
    return tab
  }
  return 'materials'
})

const currentTabMeta = computed(() => tabs.value.find((tab) => tab.key === currentTab.value) ?? tabs.value[0])

const setTab = (tab: WorkspaceTab) => {
  void router.replace({ path: '/workspace', query: { tab } })
}
</script>
