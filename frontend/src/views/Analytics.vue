<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel">
      <h2>Learning Analytics</h2>
      <p style="color: #64748b; margin-bottom: 1.5rem">Track your progress and identify areas for improvement</p>

      <div v-if="loading" style="text-align: center; padding: 2rem">Loading analytics...</div>
      
      <div v-else-if="error" class="error-panel">
        <p>{{ error }}</p>
        <button @click="loadAnalytics" class="secondary">Retry</button>
      </div>

      <div v-else class="analytics-grid">
        <!-- Stats Overview -->
        <div class="stat-card">
          <h3>Total XP</h3>
          <p class="stat-value">{{ stats.totalXp }}</p>
        </div>
        <div class="stat-card">
          <h3>Level</h3>
          <p class="stat-value">{{ stats.level }}</p>
        </div>
        <div class="stat-card">
          <h3>Current Streak</h3>
          <p class="stat-value">{{ stats.streak }} days</p>
        </div>
        <div class="stat-card">
          <h3>Lessons Completed</h3>
          <p class="stat-value">{{ stats.lessonsCompleted }}</p>
        </div>

        <!-- Hardest Words -->
        <div class="panel-section">
          <h3>Hardest Words</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">Words you've struggled with most</p>
          <ul v-if="hardestWords.length > 0" class="word-list">
            <li v-for="(word, idx) in hardestWords" :key="idx" class="word-item">
              <span class="word">{{ word.word }}</span>
              <span class="mistakes">{{ word.mistakes }} mistakes</span>
            </li>
          </ul>
          <p v-else style="color: #94a3b8">No wrong answers recorded yet</p>
        </div>

        <!-- Weakest Category -->
        <div class="panel-section">
          <h3>Weakest Category</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">Focus area for improvement</p>
          <div v-if="weakestCategory" class="category-badge">
            {{ weakestCategory.category }} ({{ weakestCategory.accuracy }}% accuracy)
          </div>
          <p v-else style="color: #94a3b8">Not enough data yet</p>
        </div>

        <!-- Accuracy Trend -->
        <div class="panel-section">
          <h3>Accuracy Trend</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">Last 5 lessons</p>
          <div class="trend-bar">
            <div
              v-for="(acc, idx) in accuracyTrend"
              :key="idx"
              class="trend-segment"
              :style="{ width: `${(acc / maxAccuracy) * 100}%`, background: getAccuracyColor(acc) }"
              :title="`Lesson ${idx + 1}: ${acc}%`"
            ></div>
          </div>
          <p v-if="accuracyTrend.length === 0" style="color: #94a3b8">Complete lessons to see trends</p>
        </div>

        <!-- Streak Trend -->
        <div class="panel-section">
          <h3>Streak History</h3>
          <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem">Recent activity</p>
          <div class="streak-grid">
            <div
              v-for="(day, idx) in streakHistory"
              :key="idx"
              class="streak-day"
              :class="{ active: day.active }"
              :title="day.label"
            >
              {{ day.label.charAt(0) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { progressApi, wrongAnswerApi, streakApi } from '@/services/api'

interface HardWord {
  word: string
  mistakes: number
}

interface CategoryStats {
  category: string
  accuracy: number
  total: number
}

interface LessonHistoryItem {
  lesson_id: string
  accuracy_rate: number
  completed_at: string
}

const loading = ref(true)
const error = ref<string | null>(null)

const stats = ref({
  totalXp: 0,
  level: 1,
  streak: 0,
  lessonsCompleted: 0,
})

const hardestWords = ref<HardWord[]>([])
const weakestCategory = ref<CategoryStats | null>(null)
const accuracyTrend = ref<number[]>([])
const streakHistory = ref<{ label: string; active: boolean }[]>([])

const maxAccuracy = computed(() => Math.max(...accuracyTrend.value, 100))

const getAccuracyColor = (acc: number): string => {
  if (acc >= 80) return '#22c55e'
  if (acc >= 60) return '#eab308'
  return '#ef4444'
}

const loadAnalytics = async () => {
  loading.value = true
  error.value = null

  try {
    // Load streak from dedicated endpoint (single source of truth)
    const streakRes = await streakApi.getStreak()
    const currentStreak = streakRes.current_streak || 0
    
    // Load progress stats
    const progressRes = await progressApi.getProgress()
    const rpgStats = progressRes.progress.rpg_stats
    stats.value = {
      totalXp: rpgStats.total_xp,
      level: rpgStats.level,
      streak: currentStreak,  // Use authoritative streak from /api/streak
      lessonsCompleted:
        (progressRes.progress.english_progress?.completed_lessons ?? 0) +
        (progressRes.progress.japanese_progress?.completed_lessons ?? 0),
    }

    // Load wrong answers for hardest words and category analysis
    try {
      const wrongRes = await wrongAnswerApi.listWrongAnswers()
      const wrongAnswers = wrongRes.items || []
      
      // Count mistakes per word
      const wordCounts = new Map<string, number>()
      wrongAnswers.forEach((ans: any) => {
        const word = ans.question || 'Unknown'
        wordCounts.set(word, (wordCounts.get(word) || 0) + 1)
      })

      // Sort by mistake count and take top 5
      hardestWords.value = Array.from(wordCounts.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([word, mistakes]) => ({ word, mistakes }))

      // Calculate weakest category based on actual wrong answer distribution
      const categoryStats = new Map<string, { count: number }>()
      wrongAnswers.forEach((ans: any) => {
        const category = ans.question_type || 'general'
        if (!categoryStats.has(category)) {
          categoryStats.set(category, { count: 0 })
        }
        categoryStats.get(category)!.count++
      })

      // Find category with most wrong answers (weakest area)
      if (categoryStats.size > 0) {
        let maxCount = 0
        let weakestCat = ''
        categoryStats.forEach((catStats, cat) => {
          if (catStats.count > maxCount) {
            maxCount = catStats.count
            weakestCat = cat
          }
        })
        if (weakestCat && maxCount > 0) {
          weakestCategory.value = {
            category: weakestCat,
            accuracy: Math.round(100 * (1 - maxCount / wrongAnswers.length)),
            total: maxCount,
          }
        }
      }
    } catch {
      // Wrong answers API might not be available
    }

    // Accuracy trend - use real data from exercise_results if available
    // For now, show empty state rather than fake data
    accuracyTrend.value = []

    // Generate streak history (last 7 days) based on actual streak count
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    const today = new Date().getDay()
    streakHistory.value = Array.from({ length: 7 }, (_, i) => {
      const dayIndex = (today - i + 7) % 7
      return {
        label: days[dayIndex],
        active: i < currentStreak,
      }
    }).reverse()

  } catch (err) {
    error.value = 'Failed to load analytics data'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(loadAnalytics)
</script>

<style scoped>
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

.stat-card h3 {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0 0 0.5rem 0;
  text-transform: uppercase;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #1e293b;
  margin: 0;
}

.panel-section {
  grid-column: span 2;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
}

.panel-section h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
}

@media (max-width: 768px) {
  .panel-section {
    grid-column: span 1;
  }
}

.word-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.word-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.word-item:last-child {
  border-bottom: none;
}

.word {
  font-weight: 500;
}

.mistakes {
  color: #ef4444;
  font-size: 0.85rem;
}

.category-badge {
  display: inline-block;
  background: #fef3c7;
  color: #92400e;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.trend-bar {
  display: flex;
  gap: 4px;
  height: 40px;
  align-items: flex-end;
}

.trend-segment {
  flex: 1;
  border-radius: 4px 4px 0 0;
  transition: all 0.2s;
}

.streak-grid {
  display: flex;
  gap: 0.5rem;
}

.streak-day {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: #64748b;
}

.streak-day.active {
  background: #22c55e;
  color: white;
  font-weight: bold;
}

.error-panel {
  text-align: center;
  padding: 2rem;
  color: #b91c1c;
}
</style>
