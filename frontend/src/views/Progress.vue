<template>
  <div class="progress-page">
    <div class="card">
      <h2>📊 學習進度</h2>
    </div>

    <div v-if="loading" class="loading">載入中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-if="progress && !loading">
      <!-- RPG Dashboard -->
      <div class="rpg-section mb-4">
        <RPGBoard v-if="progress.rpg_stats" :stats="progress.rpg_stats" />
      </div>

      <!-- AI Study Blueprint -->
      <div class="blueprint-section mb-8">
        <StudyBlueprint :language="progress.english_progress.accuracy_rate >= progress.japanese_progress.accuracy_rate ? 'EN' : 'JP'" />
      </div>

      <!-- English Progress -->
      <div class="card progress-card">
        <h3>🇬🇧 English (TOEIC)</h3>
        <div class="progress-grid">
          <div class="progress-item">
            <div class="label">當前等級</div>
            <div class="value">{{ progress.english_progress.current_level }}</div>
          </div>
          <div class="progress-item">
            <div class="label">正確率</div>
            <div class="progress-bar-container">
              <div class="progress-bar" :style="{ width: progress.english_progress.accuracy_rate + '%' }"></div>
            </div>
            <div class="value highlight">{{ progress.english_progress.accuracy_rate.toFixed(1) }}%</div>
          </div>
        </div>
      </div>

      <!-- Japanese Progress -->
      <div class="card progress-card">
        <h3>🇯🇵 日本語 (JLPT)</h3>
        <div class="progress-grid">
          <div class="progress-item">
            <div class="label">當前等級</div>
            <div class="value">{{ progress.japanese_progress.current_level }}</div>
          </div>
          <div class="progress-item">
            <div class="label">正確率</div>
            <div class="progress-bar-container">
              <div class="progress-bar" :style="{ width: progress.japanese_progress.accuracy_rate + '%' }"></div>
            </div>
            <div class="value highlight">{{ progress.japanese_progress.accuracy_rate.toFixed(1) }}%</div>
          </div>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="charts-grid" v-if="stats">
        <div class="card chart-card">
          <StatsChart :data="accuracyData" type="pie" title="語言正確率對比" />
        </div>
        <div class="card chart-card">
          <HeatmapChart :data="heatmapData" title="學習熱點圖 (2026)" />
        </div>
      </div>

      <!-- Knowledge Graph & Error Analysis -->
      <div class="charts-grid" v-if="!loading">
        <div class="card knowledge-card">
          <KnowledgeGraph :data="knowledgeData" title="語言知識圖譜 (技能樹)" />
        </div>
        <div class="card">
          <h3>⚠️ 錯誤類型分析 (Evidence)</h3>
          <div ref="errorChartRef" style="height: 300px;"></div>
          <div class="stats-grid" style="grid-template-columns: 1fr 1fr;">
            <div class="stat-item" style="padding: 10px; background: rgba(248, 113, 113, 0.1); color: #f87171;">
              <div style="font-size: 0.8rem;">拼字</div>
              <div style="font-size: 1.2rem; font-weight: bold;">{{ progress?.rpg_stats?.error_distribution?.spelling || 0 }}</div>
            </div>
            <div class="stat-item" style="padding: 10px; background: rgba(251, 191, 36, 0.1); color: #fbbf24;">
              <div style="font-size: 0.8rem;">文法</div>
              <div style="font-size: 1.2rem; font-weight: bold;">{{ progress?.rpg_stats?.error_distribution?.grammar || 0 }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Achievements & Cards -->
      <div class="gamification-grid mt-4">
        <div class="card">
          <h3>🏆 成就勳章</h3>
          <div class="achievements-wall" v-if="progress.rpg_stats?.achievements?.length">
            <div v-for="ach in progress.rpg_stats.achievements" :key="ach.id" class="achievement-item" :title="ach.description">
              <span class="ach-icon">{{ ach.icon }}</span>
              <span class="ach-title">{{ ach.title }}</span>
            </div>
          </div>
          <p v-else class="text-center opacity-60">尚未解鎖任何成就</p>
        </div>
        <div class="card">
          <h3>🃏 單字卡牌收集</h3>
          <div class="cards-container" v-if="progress.rpg_stats?.word_cards?.length">
            <div class="cards-scroll">
              <WordCard v-for="card in progress.rpg_stats.word_cards" :key="card.word" :card="card" />
            </div>
          </div>
          <p v-else class="text-center opacity-60">開始學習以收集卡牌</p>
        </div>
      </div>

      <!-- Overall Statistics -->
      <div class="card" v-if="stats">
        <h3>📈 整體統計</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">{{ stats.total_lessons }}</div>
            <div class="stat-label">總課程數</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ stats.english_lessons }}</div>
            <div class="stat-label">英語課程</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ stats.japanese_lessons }}</div>
            <div class="stat-label">日語課程</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ stats.total_exercises }}</div>
            <div class="stat-label">總練習題</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ stats.overall_accuracy }}%</div>
            <div class="stat-label">整體正確率</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { progressApi, statsApi } from '../services/api'
import type { UserProgress } from '../types'
import StatsChart from '../components/StatsChart.vue'
import KnowledgeGraph from '../components/KnowledgeGraph.vue'
import HeatmapChart from '../components/HeatmapChart.vue'
import RPGBoard from '../components/RPGBoard.vue'
import WordCard from '../components/WordCard.vue'
import StudyBlueprint from '../components/StudyBlueprint.vue'
import * as echarts from 'echarts'

const progress = ref<UserProgress | null>(null)
const stats = ref<any>(null)
const loading = ref(false)
const error = ref('')
const errorChartRef = ref<HTMLElement | null>(null)

const initErrorChart = () => {
  if (!errorChartRef.value || !progress.value?.rpg_stats?.error_distribution) return
  const chart = echarts.init(errorChartRef.value)
  const dist = progress.value.rpg_stats.error_distribution
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#1e293b', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: dist.spelling || 0, name: '拼字錯誤', itemStyle: { color: '#f87171' } },
        { value: dist.grammar || 0, name: '文法錯誤', itemStyle: { color: '#fbbf24' } },
        { value: dist.vocabulary || 0, name: '詞彙錯誤', itemStyle: { color: '#60a5fa' } },
        { value: dist.comprehension || 0, name: '理解錯誤', itemStyle: { color: '#a78bfa' } }
      ]
    }]
  })
}

const accuracyData = computed(() => {
  if (!stats.value) return []
  return [
    { value: stats.value.english_accuracy, name: 'English' },
    { value: stats.value.japanese_accuracy, name: 'Japanese' }
  ]
})

const streak = ref(5) // Mock streak data

// Mock Knowledge Graph Data
const knowledgeData = {
  nodes: [
    { name: 'English', category: 0, value: 100 },
    { name: 'Grammar', category: 1, value: 80 },
    { name: 'Tenses', category: 2, value: 60 },
    { name: 'Vocabulary', category: 1, value: 90 },
    { name: 'Business', category: 2, value: 70 },
    { name: 'Japanese', category: 0, value: 100 },
    { name: 'JLPT N3', category: 1, value: 50 },
    { name: 'Kanji', category: 2, value: 40 }
  ],
  links: [
    { source: 'English', target: 'Grammar' },
    { source: 'Grammar', target: 'Tenses' },
    { source: 'English', target: 'Vocabulary' },
    { source: 'Vocabulary', target: 'Business' },
    { source: 'Japanese', target: 'JLPT N3' },
    { source: 'JLPT N3', target: 'Kanji' }
  ]
}

// Mock Heatmap Data
const heatmapData = [
  ['2026-01-01', 5], ['2026-01-02', 8], ['2026-01-03', 2],
  ['2026-01-04', 0], ['2026-01-05', 10], ['2026-01-06', 4],
  ['2026-01-07', 7], ['2026-01-08', 3], ['2026-01-09', 6],
  ['2026-01-10', 9], ['2026-01-11', 1], ['2026-01-12', 5]
]

const loadProgress = async () => {
  loading.value = true
  error.value = ''
  try {
    const [progressRes, statsRes] = await Promise.all([
      progressApi.getProgress(),
      statsApi.getStatistics()
    ])
    progress.value = progressRes.progress
    stats.value = statsRes.stats
  } catch (err: any) {
    error.value = err.message || '載入失敗'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-TW')
}

onMounted(async () => {
  await loadProgress()
  setTimeout(initErrorChart, 500)
})
</script>

<style scoped>
.streak-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
  margin-bottom: 2rem;
  padding: 1.5rem 2rem;
  color: #d81b60;
}

.streak-content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.streak-icon {
  font-size: 3rem;
}

.badge-icon {
  font-size: 2rem;
  margin-left: 1rem;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

.progress-bar-container {
  flex: 1;
  height: 8px;
  background: #eee;
  border-radius: 4px;
  margin: 10px 0;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #667eea;
  border-radius: 4px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.progress-card {
  margin-bottom: 30px;
}

.progress-card h3 {
  color: #667eea;
  margin-bottom: 20px;
}

.progress-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 15px;
}

.progress-item {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.label {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 10px;
}

.value {
  font-size: 2rem;
  font-weight: bold;
  color: #333;
}

.value.highlight {
  color: #667eea;
}

.last-study {
  color: #666;
  font-size: 0.9rem;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  color: white;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 10px;
}

.stat-label {
  font-size: 0.9rem;
  opacity: 0.9;
}

.gamification-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.achievements-wall {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
}

.achievement-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 80px;
  text-align: center;
}

.ach-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.ach-title {
  font-size: 0.75rem;
  font-weight: bold;
}

.cards-container {
  overflow: hidden;
}

.cards-scroll {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding: 1rem 0;
}

.cards-scroll::-webkit-scrollbar {
  height: 6px;
}

.cards-scroll::-webkit-scrollbar-thumb {
  background: var(--primary-color);
  border-radius: 3px;
}
</style>
