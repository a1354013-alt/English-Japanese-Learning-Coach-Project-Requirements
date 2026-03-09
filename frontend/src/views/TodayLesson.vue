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

const checkAnswer = async (type: 'grammar' | 'reading', index: number, answer: any) => {
  if (!lesson.value) return
  
  const exercises = type === 'grammar' ? lesson.value.grammar.exercises : lesson.value.reading.questions
  const exercise = exercises[index]
  const isCorrect = String(answer) === String(exercise.correct_answer)
  
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
      is_correct: isCorrect
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

const getAnswerClass = (type: 'grammar' | 'reading', index: number, optIdx: number) => {
  const result = results.value[type][index]
  if (!result) return 'hover:bg-white/5'
  
  const isSelected = userAnswers.value[type][index] === optIdx
  const isCorrect = optIdx === lesson.value?.[type === 'grammar' ? 'grammar' : 'reading'].questions[index].correct_answer
  
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
  // Redirect or show summary
}

const exportPdf = () => {
  if (lesson.value) {
    lessonApi.exportPdf(lesson.value.metadata.lesson_id)
  }
}

const playTts = (text: string) => {
  // TTS implementation
  console.log('Playing TTS for:', text)
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
              <p class="text-slate-300 mb-4"><span class="text-blue-500 font-bold">定義：</span>{{ word.definition || word.definition_zh }}</p>
              <div class="bg-slate-900/50 p-3 rounded-xl border border-white/5">
                <p class="text-xs text-slate-400 italic">"{{ word.example || word.example_sentence }}"</p>
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
                    @click="checkAnswer('grammar', idx, optIdx)"
                    class="px-4 py-3 rounded-xl border border-white/10 text-left text-sm transition-all"
                    :class="getAnswerClass('grammar', idx, optIdx)"
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
          <div class="flex justify-between">
            <button @click="currentStep--" class="glass-panel px-8 py-3 rounded-xl font-bold text-white">上一步</button>
            <button @click="nextStep" class="btn-3d bg-blue-600 px-8 py-3 rounded-xl font-bold text-white">下一步：短篇閱讀</button>
          </div>
        </div>

        <!-- Step 2: Reading -->
        <div v-if="currentStep === 2" class="space-y-6">
          <div class="glass-panel p-8 rounded-3xl">
            <h2 class="text-2xl font-bold text-white mb-6">閱讀理解：{{ lesson.reading.title }}</h2>
            <div class="bg-slate-900/80 p-8 rounded-2xl border border-white/5 mb-8">
              <p class="text-xl text-slate-200 leading-loose font-serif whitespace-pre-wrap">{{ lesson.reading.content }}</p>
            </div>
            
            <h3 class="text-lg font-bold text-white mb-4">理解題</h3>
            <div class="space-y-6">
              <div v-for="(q, idx) in lesson.reading.questions" :key="idx" class="p-6 rounded-2xl bg-slate-900/50 border border-white/5">
                <p class="text-white font-bold mb-4">{{ idx + 1 }}. {{ q.question }}</p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <button 
                    v-for="(opt, optIdx) in q.options" 
                    :key="optIdx"
                    @click="checkAnswer('reading', idx, optIdx)"
                    class="px-4 py-3 rounded-xl border border-white/10 text-left text-sm transition-all"
                    :class="getAnswerClass('reading', idx, optIdx)"
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
          <div class="flex justify-between">
            <button @click="currentStep--" class="glass-panel px-8 py-3 rounded-xl font-bold text-white">上一步</button>
            <button @click="nextStep" class="btn-3d bg-blue-600 px-8 py-3 rounded-xl font-bold text-white">下一步：情境對話</button>
          </div>
        </div>

        <!-- Step 3: Dialogue -->
        <div v-if="currentStep === 3" class="space-y-6">
          <div class="glass-panel p-8 rounded-3xl">
            <h2 class="text-2xl font-bold text-white mb-6">情境對話：{{ lesson.dialogue.scenario }}</h2>
            <div class="space-y-4">
              <div v-for="(line, idx) in (lesson.dialogue.dialogue || lesson.dialogue.lines)" :key="idx" 
                class="flex gap-4" :class="idx % 2 === 0 ? 'flex-row' : 'flex-row-reverse'">
                <div class="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center font-bold text-white shrink-0">
                  {{ (line.speaker || line.role)[0] }}
                </div>
                <div class="glass-panel p-4 rounded-2xl max-w-[80%]" :class="idx % 2 === 0 ? 'rounded-tl-none' : 'rounded-tr-none'">
                  <p class="text-white">{{ line.text || line.content }}</p>
                  <p class="text-slate-500 text-xs mt-1">{{ line.translation }}</p>
                </div>
              </div>
            </div>
          </div>
          <div class="flex justify-between">
            <button @click="currentStep--" class="glass-panel px-8 py-3 rounded-xl font-bold text-white">上一步</button>
            <button @click="finishLesson" class="btn-3d bg-green-600 px-8 py-3 rounded-xl font-bold text-white">完成課程並領取獎勵！</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Generate Dialog -->
    <div v-if="showGenerateDialog" class="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div class="glass-panel p-8 rounded-3xl w-full max-w-md animate__animated animate__zoomIn">
        <h3 class="text-2xl font-bold text-white mb-6">生成新課程</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-bold text-slate-400 mb-2">語言</label>
            <select v-model="generateForm.language" class="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-2 text-white">
              <option value="EN">English</option>
              <option value="JP">日本語</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-bold text-slate-400 mb-2">主題 (選填)</label>
            <input v-model="generateForm.topic" class="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-2 text-white" placeholder="如：商務會議、旅遊..." />
          </div>
          <div>
            <label class="block text-sm font-bold text-slate-400 mb-2">難度</label>
            <select v-model="generateForm.difficulty" class="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-2 text-white">
              <option v-if="generateForm.language === 'EN'" v-for="l in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']" :key="l" :value="l">{{ l }}</option>
              <option v-if="generateForm.language === 'JP'" v-for="l in ['N5', 'N4', 'N3', 'N2', 'N1']" :key="l" :value="l">{{ l }}</option>
            </select>
          </div>
        </div>
        <div class="flex gap-3 mt-8">
          <button @click="showGenerateDialog = false" class="flex-1 px-4 py-3 rounded-xl text-slate-400 font-bold hover:bg-white/5">取消</button>
          <button @click="generateNewLesson" class="flex-1 btn-3d bg-blue-600 px-4 py-3 rounded-xl text-white font-bold">開始生成</button>
        </div>
      </div>
    </div>
  </div>
</template>
