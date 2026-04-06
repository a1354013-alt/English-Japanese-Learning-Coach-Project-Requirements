<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { lessonApi, reviewApi } from '../services/api'
import type { Lesson } from '../types'
import confetti from 'canvas-confetti'

const currentLanguage = ref<'EN' | 'JP'>('EN')
const lesson = ref<Lesson | null>(null)
const loading = ref(false)
const currentStep = ref(0)
const completedSteps = ref<number[]>([])
const difficultyMode = ref('normal')
const fatigueWarning = ref(false)
const showGenerateDialog = ref(false)

const generateForm = ref({
  language: 'EN',
  topic: '',
  difficulty: 'B1'
})

const steps = [
  { label: '核心單字', icon: 'pi pi-list' },
  { label: '文法解析', icon: 'pi pi-book' },
  { label: '短篇閱讀', icon: 'pi pi-align-left' },
  { label: '情境對話', icon: 'pi pi-comments' }
]

const userAnswers = ref({
  grammar: {} as Record<number, any>,
  reading: {} as Record<number, any>
})

const results = ref({
  grammar: {} as Record<number, any>,
  reading: {} as Record<number, any>
})

const fetchTodayLesson = async () => {
  loading.value = true
  try {
    const res = await lessonApi.getTodayLesson(currentLanguage.value)
    if (res.success && res.lesson) {
      lesson.value = res.lesson
    } else {
      lesson.value = null
    }
  } catch (error) {
    console.error('Failed to fetch today lesson:', error)
  } finally {
    loading.value = false
  }
}

const generateNewLesson = async () => {
  loading.value = true
  showGenerateDialog.value = false
  try {
    const res = await lessonApi.generateLesson({
      language: generateForm.value.language as 'EN' | 'JP',
      topic: generateForm.value.topic || undefined,
      difficulty: generateForm.value.difficulty
    })
    if (res.success) {
      lesson.value = res.lesson
      currentLanguage.value = generateForm.value.language as 'EN' | 'JP'
      currentStep.value = 0
      completedSteps.value = []
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 }
      })
    }
  } catch (error) {
    console.error('Failed to generate lesson:', error)
  } finally {
    loading.value = false
  }
}

const resolveCorrectAnswerText = (exercise: any) => {
  // correct_answer is now always stored as text (normalized during lesson generation)
  return String(exercise.correct_answer)
}

const checkAnswer = async (type: 'grammar' | 'reading', index: number, answer: any) => {
  if (!lesson.value) return
  
  const exercises = type === 'grammar' ? lesson.value.grammar.exercises : lesson.value.reading.questions
  const exercise = exercises[index]
  
  const correct_text = resolveCorrectAnswerText(exercise)
  
  // Use string-based comparison
  const isCorrect = String(answer).trim().toLowerCase() === String(correct_text).trim().toLowerCase()
  
  results.value[type][index] = {
    is_correct: isCorrect,
    explanation: exercise.explanation
  }

  // Submit to backend for tracking and XP
  try {
    await reviewApi.submitReview([{
      lesson_id: lesson.value.metadata.lesson_id,
      exercise_type: type,
      question_index: index,
      user_answer: String(answer),
      correct_answer: String(correct_text)
    }], 'default_user', type)
  } catch (e) {
    console.error('Failed to submit review:', e)
  }

  if (isCorrect) {
    confetti({
      particleCount: 40,
      spread: 50,
      origin: { y: 0.8 },
      colors: ['#10b981', '#34d399']
    })
  }
}

const getAnswerClass = (type: 'grammar' | 'reading', index: number, opt: string) => {
  const result = results.value[type][index]
  if (!result) return 'hover:bg-white/5'
  
  const isSelected = userAnswers.value[type][index] === opt
  
  const exercise = type === 'grammar' 
    ? lesson.value?.grammar.exercises[index] 
    : lesson.value?.reading.questions[index]
  
  const correct_text = resolveCorrectAnswerText(exercise)
  
  // String-based comparison (consistent with checkAnswer)
  const isCorrect = String(opt).trim().toLowerCase() === String(correct_text).trim().toLowerCase()
  
  if (isCorrect) return 'bg-green-500/20 border-green-500 text-green-400'
  if (isSelected && !isCorrect) return 'bg-red-500/20 border-red-500 text-red-400'
  return 'opacity-50'
}

const nextStep = () => {
  if (!completedSteps.value.includes(currentStep.value)) {
    completedSteps.value.push(currentStep.value)
  }
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const finishLesson = () => {
  confetti({
    particleCount: 200,
    spread: 100,
    origin: { y: 0.6 }
  })
}

const exportPdf = () => {
  if (lesson.value) {
    lessonApi.exportPdf(lesson.value.metadata.lesson_id)
  }
}

const playTts = async (text: string) => {
  try {
    const res = await lessonApi.getTts(text, currentLanguage.value)
    if (res.audio_url) {
      const audio = new Audio(res.audio_url)
      audio.play()
    }
  } catch (e) {
    console.error('Failed to play TTS:', e)
  }
}

onMounted(fetchTodayLesson)
watch(currentLanguage, fetchTodayLesson)

</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="bg-mesh"></div>
    
    <!-- Header -->
    <div class="flex justify-between items-center mb-8 animate__animated animate__fadeIn">
      <div>
        <h1 class="text-4xl font-black text-white tracking-tight">今日課程</h1>
        <p class="text-slate-400 mt-1">{{ lesson?.metadata.topic || '載入中...' }} • {{ currentLanguage === 'EN' ? 'English' : 'Japanese' }}</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="glass-panel px-3 py-1 rounded-xl flex gap-1">
          <button v-for="m in ['easy', 'normal', 'hardcore']" :key="m" 
            @click="difficultyMode = m"
            :class="['px-2 py-1 rounded-lg text-[10px] font-bold transition-all', difficultyMode === m ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-300']">
            {{ m.toUpperCase() }}
          </button>
        </div>
        <button @click="exportPdf" v-if="lesson" class="glass-panel px-4 py-2 rounded-xl text-sm font-bold text-white hover-glow flex items-center gap-2">
          <i class="pi pi-file-pdf"></i> 匯出 PDF
        </button>
        <button @click="showGenerateDialog = true" class="btn-3d bg-blue-600 px-6 py-2 rounded-xl text-sm font-bold text-white hover:bg-blue-500">
          生成新課程
        </button>
      </div>
    </div>

    <!-- Fatigue Warning -->
    <div v-if="fatigueWarning" class="glass-panel border-l-4 border-yellow-500 p-4 mb-8 animate__animated animate__shakeX">
      <div class="flex items-center gap-3">
        <span class="text-2xl">🧘</span>
        <div>
          <div class="font-bold text-yellow-500">偵測到學習疲勞</div>
          <div class="text-sm text-slate-400">您的正確率有所下降，建議切換至「輕鬆模式」或休息一下再繼續。</div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex flex-col items-center justify-center h-64">
      <i class="pi pi-spin pi-spinner text-4xl text-blue-500 mb-4"></i>
      <p class="text-slate-400 animate-pulse">AI 正在為您量身打造課程...</p>
    </div>

    <div v-else-if="lesson" class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <!-- Left: Navigation Path -->
      <div class="lg:col-span-3">
        <div class="glass-panel rounded-2xl p-4 sticky top-8">
          <h3 class="text-xs font-bold text-slate-500 uppercase tracking-widest mb-6 px-2">學習路徑</h3>
          <div class="space-y-2">
            <button 
              v-for="(step, index) in steps" 
              :key="index"
              @click="currentStep = index"
              class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all"
              :class="currentStep === index ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' : 'text-slate-400 hover:bg-white/5'"
            >
              <i :class="step.icon"></i>
              <span class="font-bold text-sm">{{ step.label }}</span>
              <i v-if="completedSteps.includes(index)" class="pi pi-check-circle ml-auto text-green-400"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Right: Content Area -->
      <div class="lg:col-span-9 space-y-8 animate__animated animate__fadeInRight">
        <!-- Step 0: Vocabulary -->
        <div v-if="currentStep === 0" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="(word, idx) in lesson.vocabulary" :key="idx" class="glass-panel p-6 rounded-2xl hover-glow group">
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h3 class="text-2xl font-bold text-white">{{ word.word }}</h3>
                  <p class="text-blue-400 font-mono text-sm">{{ word.phonetic || word.reading || word.reading_kana }}</p>
                </div>
                <button @click="playTts(word.word)" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-blue-500/20 transition-colors">
                  <i class="pi pi-volume-up text-blue-400"></i>
                </button>
              </div>
              <p class="text-slate-300 mb-4"><span class="text-blue-500 font-bold">定義：</span>{{ word.definition_zh }}</p>
              <div class="bg-slate-900/50 p-3 rounded-xl border border-white/5">
                <p class="text-xs text-slate-400 italic">"{{ word.example_sentence }}"</p>
                <p class="text-[10px] text-slate-500 mt-1">{{ word.example_translation }}</p>
              </div>
            </div>
          </div>
          <div class="flex justify-end">
            <button @click="nextStep" class="btn-3d bg-blue-600 px-8 py-3 rounded-xl font-bold text-white">下一步：文法解析</button>
          </div>
        </div>

        <!-- Step 1: Grammar -->
        <div v-if="currentStep === 1" class="space-y-6">
          <div class="glass-panel p-8 rounded-3xl">
            <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <i class="pi pi-book text-purple-400"></i> 文法重點：{{ lesson.grammar.title }}
            </h2>
            <div class="prose prose-invert max-w-none mb-8">
              <p class="text-slate-300 leading-relaxed">{{ lesson.grammar.explanation }}</p>
            </div>
            
            <h3 class="text-lg font-bold text-white mb-4">練習題</h3>
            <div class="space-y-6">
              <div v-for="(ex, idx) in lesson.grammar.exercises" :key="idx" class="p-6 rounded-2xl bg-slate-900/50 border border-white/5">
                <p class="text-white font-bold mb-4">{{ idx + 1 }}. {{ ex.question }}</p>
                <div v-if="ex.options" class="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <button 
                    v-for="(opt, optIdx) in ex.options" 
                    :key="optIdx"
                    @click="userAnswers.grammar[idx] = opt; checkAnswer('grammar', idx, opt)"
                    class="px-4 py-3 rounded-xl border border-white/10 text-left text-sm transition-all"
                    :class="getAnswerClass('grammar', idx, opt)"
                  >
                    {{ opt }}
                  </button>
                </div>
                <div v-else class="flex gap-2">
                  <input 
                    v-model="userAnswers.grammar[idx]" 
                    class="bg-slate-800 border border-white/10 rounded-xl px-4 py-2 text-white flex-1"
                    placeholder="輸入答案..."
                  />
                  <button @click="checkAnswer('grammar', idx, userAnswers.grammar[idx])" class="bg-blue-600 px-4 py-2 rounded-xl font-bold text-white">提交</button>
                </div>
                <p v-if="results.grammar[idx]" class="mt-4 text-sm" :class="results.grammar[idx].is_correct ? 'text-green-400' : 'text-red-400'">
                  {{ results.grammar[idx].is_correct ? '✅ 正確！' : '❌ 錯誤。' }} {{ results.grammar[idx].explanation }}
                </p>
              </div>
            </div>
          </div>
          <div class="flex justify-end">
            <button @click="nextStep" class="btn-3d bg-blue-600 px-8 py-3 rounded-xl font-bold text-white">下一步：短篇閱讀</button>
          </div>
        </div>

        <!-- Step 2: Reading -->
        <div v-if="currentStep === 2" class="space-y-6">
          <div class="glass-panel p-8 rounded-3xl">
            <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <i class="pi pi-align-left text-green-400"></i> 閱讀理解
            </h2>
            <div class="bg-slate-900/50 p-6 rounded-2xl border border-white/5 mb-8">
              <p class="text-slate-200 leading-relaxed text-lg whitespace-pre-wrap">{{ lesson.reading.content }}</p>
            </div>
            
            <h3 class="text-lg font-bold text-white mb-4">理解測試</h3>
            <div class="space-y-6">
              <div v-for="(q, idx) in lesson.reading.questions" :key="idx" class="p-6 rounded-2xl bg-slate-900/50 border border-white/5">
                <p class="text-white font-bold mb-4">{{ idx + 1 }}. {{ q.question }}</p>
                <div class="grid grid-cols-1 gap-3">
                  <button 
                    v-for="(opt, optIdx) in q.options" 
                    :key="optIdx"
                    @click="userAnswers.reading[idx] = opt; checkAnswer('reading', idx, opt)"
                    class="px-4 py-3 rounded-xl border border-white/10 text-left text-sm transition-all"
                    :class="getAnswerClass('reading', idx, opt)"
                  >
                    {{ opt }}
                  </button>
                </div>
                <p v-if="results.reading[idx]" class="mt-4 text-sm" :class="results.reading[idx].is_correct ? 'text-green-400' : 'text-red-400'">
                  {{ results.reading[idx].is_correct ? '✅ 正確！' : '❌ 錯誤。' }} {{ results.reading[idx].explanation }}
                </p>
              </div>
            </div>
          </div>
          <div class="flex justify-end">
            <button @click="nextStep" class="btn-3d bg-blue-600 px-8 py-3 rounded-xl font-bold text-white">下一步：情境對話</button>
          </div>
        </div>

        <!-- Step 3: Dialogue -->
        <div v-if="currentStep === 3" class="space-y-6">
          <div class="glass-panel p-8 rounded-3xl">
            <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <i class="pi pi-comments text-orange-400"></i> 情境對話：{{ lesson.dialogue.scenario }}
            </h2>
            <div class="space-y-4 mb-8">
              <div v-for="(line, idx) in lesson.dialogue.dialogue" :key="idx" 
                class="flex flex-col" :class="idx % 2 === 0 ? 'items-start' : 'items-end'">
                <div class="max-w-[80%] p-4 rounded-2xl" 
                  :class="idx % 2 === 0 ? 'bg-slate-800 text-white rounded-tl-none' : 'bg-blue-600 text-white rounded-tr-none'">
                  <div class="text-[10px] opacity-60 mb-1 font-bold uppercase">{{ line.speaker }}</div>
                  <p class="text-sm">{{ line.text }}</p>
                  <p class="text-[10px] opacity-80 mt-1">{{ line.translation }}</p>
                </div>
              </div>
            </div>
            
            <div class="bg-orange-500/10 border border-orange-500/20 p-6 rounded-2xl">
              <h3 class="text-orange-400 font-bold mb-3 flex items-center gap-2">
                <i class="pi pi-bolt"></i> 替換句型
              </h3>
              <div class="space-y-3">
                <div v-for="(alternative, idx) in lesson.dialogue.alternatives" :key="idx" class="text-sm">
                  <div class="text-white font-bold">{{ alternative.original }}</div>
                  <div class="text-slate-400 mt-1">💡 可以替換為：</div>
                  <ul class="list-disc list-inside text-blue-400 mt-1">
                    <li>{{ alternative.alternative }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-4">
            <button @click="finishLesson" class="btn-3d bg-green-600 px-8 py-3 rounded-xl font-bold text-white">完成今日課程！</button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center h-64 glass-panel rounded-3xl">
      <p class="text-slate-400 mb-6">今天還沒有生成課程喔！</p>
      <button @click="showGenerateDialog = true" class="btn-3d bg-blue-600 px-8 py-3 rounded-xl font-bold text-white">
        立即生成第一課
      </button>
    </div>

    <!-- Generate Dialog -->
    <div v-if="showGenerateDialog" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div class="glass-panel p-8 rounded-3xl w-full max-w-md animate__animated animate__zoomIn">
        <h2 class="text-2xl font-bold text-white mb-6">自訂新課程</h2>
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-2">學習語言</label>
            <div class="grid grid-cols-2 gap-2">
              <button @click="generateForm.language = 'EN'" 
                :class="['py-2 rounded-xl font-bold transition-all', generateForm.language === 'EN' ? 'bg-blue-600 text-white' : 'bg-white/5 text-slate-400']">
                English
              </button>
              <button @click="generateForm.language = 'JP'" 
                :class="['py-2 rounded-xl font-bold transition-all', generateForm.language === 'JP' ? 'bg-blue-600 text-white' : 'bg-white/5 text-slate-400']">
                Japanese
              </button>
            </div>
          </div>
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-2">主題 (選填)</label>
            <input v-model="generateForm.topic" placeholder="例如：旅遊、商務、美食..." 
              class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase mb-2">難度等級</label>
            <select v-model="generateForm.difficulty" class="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-3 text-white outline-none">
              <option v-if="generateForm.language === 'EN'" value="A1">A1 - 入門</option>
              <option v-if="generateForm.language === 'EN'" value="A2">A2 - 初級</option>
              <option v-if="generateForm.language === 'EN'" value="B1">B1 - 中級</option>
              <option v-if="generateForm.language === 'EN'" value="B2">B2 - 中高</option>
              <option v-if="generateForm.language === 'JP'" value="N5">N5 - 五十音/初級</option>
              <option v-if="generateForm.language === 'JP'" value="N4">N4 - 基礎</option>
              <option v-if="generateForm.language === 'JP'" value="N3">N3 - 中級</option>
              <option v-if="generateForm.language === 'JP'" value="N2">N2 - 進階</option>
            </select>
          </div>
        </div>
        <div class="flex gap-3 mt-8">
          <button @click="showGenerateDialog = false" class="flex-1 py-3 rounded-xl font-bold text-slate-400 hover:bg-white/5">取消</button>
          <button @click="generateNewLesson" class="flex-1 btn-3d bg-blue-600 py-3 rounded-xl font-bold text-white">開始生成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bg-mesh {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(147, 51, 234, 0.15) 0px, transparent 50%);
  z-index: -1;
}

.glass-panel {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.hover-glow:hover {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.3);
}

.btn-3d {
  transition: all 0.2s;
  box-shadow: 0 4px 0 rgba(0, 0, 0, 0.2);
}

.btn-3d:active {
  transform: translateY(2px);
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.2);
}
</style>
