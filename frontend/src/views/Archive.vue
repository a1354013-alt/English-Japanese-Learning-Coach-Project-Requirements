<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="bg-mesh"></div>
    
    <!-- Header -->
    <div class="flex justify-between items-center mb-8 animate__animated animate__fadeIn">
      <div>
        <h1 class="text-4xl font-black text-white tracking-tight">課程歸檔</h1>
        <p class="text-slate-400 mt-1">瀏覽歷史課程、匯入單字或上傳學習素材</p>
      </div>
    </div>

    <!-- Import Section -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
      <div class="glass-panel p-8 rounded-3xl border-2 border-dashed border-white/10 hover:border-blue-500/50 transition-all group">
        <div class="flex flex-col items-center text-center">
          <div class="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <i class="pi pi-file-excel text-3xl text-blue-400"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">Excel 批次匯入單字</h3>
          <p class="text-slate-400 text-sm mb-6">上傳包含 word, definition 欄位的 Excel 檔案，快速建立您的專屬單字庫。</p>
          <input type="file" ref="excelInput" class="hidden" accept=".xlsx, .xls" @change="handleExcelUpload" />
          <button @click="excelInput?.click()" class="btn-3d bg-blue-600 px-8 py-2 rounded-xl font-bold text-white">
            選擇檔案
          </button>
        </div>
      </div>

      <div class="glass-panel p-8 rounded-3xl border-2 border-dashed border-white/10 hover:border-purple-500/50 transition-all group">
        <div class="flex flex-col items-center text-center">
          <div class="w-16 h-16 bg-purple-600/20 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <i class="pi pi-cloud-upload text-3xl text-purple-400"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">個人化 RAG 素材</h3>
          <p class="text-slate-400 text-sm mb-6">上傳感興趣的文章 (TXT)，AI 將根據這些內容為您生成專屬課程。</p>
          <input type="file" ref="ragInput" class="hidden" accept=".txt" @change="handleRagUpload" />
          <button @click="ragInput?.click()" class="btn-3d bg-purple-600 px-8 py-2 rounded-xl font-bold text-white">
            上傳素材
          </button>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="glass-panel p-6 rounded-2xl mb-8 flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[200px]">
        <label class="block text-xs font-bold text-slate-500 uppercase mb-2">語言</label>
        <select v-model="filters.language" class="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-2 text-white">
          <option value="">全部</option>
          <option value="EN">English</option>
          <option value="JP">日本語</option>
        </select>
      </div>
      <div class="flex-1 min-w-[200px]">
        <label class="block text-xs font-bold text-slate-500 uppercase mb-2">主題</label>
        <input v-model="filters.topic" class="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-2 text-white" placeholder="搜尋主題..." />
      </div>
      <button @click="loadLessons" class="glass-panel px-6 py-2 rounded-xl font-bold text-white hover:bg-white/10">
        篩選
      </button>
    </div>

    <!-- Lessons Grid -->
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spin pi-spinner text-3xl text-blue-500"></i>
    </div>
    <div v-else-if="lessons.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="lesson in lessons" :key="lesson.lesson_id" class="glass-panel p-6 rounded-2xl hover-glow animate__animated animate__fadeInUp">
        <div class="flex justify-between items-start mb-4">
          <span class="px-3 py-1 rounded-full bg-blue-600/20 text-blue-400 text-xs font-bold">{{ lesson.level }}</span>
          <span class="text-xs text-slate-500">{{ formatDate(lesson.generated_at) }}</span>
        </div>
        <h3 class="text-xl font-bold text-white mb-2">{{ lesson.topic }}</h3>
        <p class="text-slate-400 text-sm mb-6 line-clamp-2">{{ parseKeyPoints(lesson.key_points).join(', ') }}</p>
        <button @click="viewLesson(lesson.lesson_id)" class="w-full py-2 rounded-xl bg-white/5 text-white font-bold hover:bg-blue-600 transition-all">
          查看課程
        </button>
      </div>
    </div>
    <div v-else class="text-center py-12 glass-panel rounded-2xl">
      <p class="text-slate-500">尚未有符合條件的課程</p>
    </div>

    <!-- Task History -->
    <TaskHistory />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { lessonApi, importApi } from '../services/api';
import confetti from 'canvas-confetti';
import TaskHistory from '../components/TaskHistory.vue';

const lessons = ref<any[]>([]);
const loading = ref(true);
const excelInput = ref<HTMLInputElement | null>(null);
const ragInput = ref<HTMLInputElement | null>(null);

const filters = ref({
  language: '',
  level: '',
  topic: '',
  start_date: '',
  end_date: ''
});

onMounted(async () => {
  await loadLessons();
});

const loadLessons = async () => {
  loading.value = true;
  try {
    const params: any = { limit: 50 };
    if (filters.value.language) params.language = filters.value.language;
    if (filters.value.topic) params.topic = filters.value.topic;
    
    const res = await lessonApi.listLessons(params);
    lessons.value = res.lessons;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const handleExcelUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  try {
    const res = await importApi.importExcel('EN', file);
    alert(`成功匯入 ${res.count} 個單字！`);
    confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
  } catch (e) {
    alert('匯入失敗：' + e);
  }
};

const handleRagUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  try {
    await importApi.uploadRagMaterial('EN', file);
    alert('素材上傳成功！AI 將在生成下一課時參考此內容。');
    confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 }, colors: ['#a855f7'] });
  } catch (e) {
    alert('上傳失敗：' + e);
  }
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-TW');
};

const parseKeyPoints = (keyPoints: any) => {
  if (Array.isArray(keyPoints)) return keyPoints;
  try {
    return JSON.parse(keyPoints);
  } catch {
    return [keyPoints];
  }
};

const viewLesson = (id: string) => {
  // 導向課程詳情 (假設有此路由)
  window.location.href = `/lesson/${id}`;
};
</script>
