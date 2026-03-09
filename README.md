# English-Japanese-Learning-Coach-Project-Requirements
AI-Powered Language Learning Lab: A self-hosted EN/JP course generator using FastAPI, Vue 3, and local Ollama (LLM).
) 前端：Vue 3 + Vite + TypeScript + PrimeVue（或簡單 UI 也可），提供：
   - 今日課程頁：顯示英語/日語課程內容（單字、文法、閱讀、對話、練習題）
   - 進度頁：顯示 TOEIC 與 JLPT 進度（等級、已完成課數、正確率）
   - 歸檔頁：可以瀏覽歷史課程（依日期、語言、難度、主題篩選）
   - 生成按鈕：可手動生成「下一課」，並可選語言(EN/JP)、主題、難度

2) 後端：Python 3.11 + FastAPI
   - /api/generate/lesson  POST：依使用者進度生成新課程（呼叫本地 Ollama）
   - /api/lessons         GET：列出已歸檔課程（支援查詢條件）
   - /api/lessons/{id}    GET：取得單一課程
   - /api/progress        GET/POST：讀寫進度（TOEIC 目標 700；日文從五十音到 N2）
   - /api/review          POST：提交練習題答案，回傳解析與錯題本

3) 本地 AI：串接 Ollama（http://localhost:11434）
   - 使用 13B 中等模型（以設定檔指定 model name）
   - 後端需有一個 ollama_client.py 封裝呼叫（含 timeout、重試、錯誤處理）

4) 課程生成內容（EN/JP 都要支援）：
   - 單詞列表：詞/假名/音標(英文)/定義(中文)/例句/例句翻譯/同反義(英文可選)
   - 音頻：先產出 TTS 腳本文字與檔名規劃即可（不用真的做 TTS 也行，但預留介面）
   - 文法解釋：含 3~5 個例句 + 5 題練習（含答案與解析）
   - 短篇閱讀：300~450 字英文；日文 250~400 字（依等級調整），附 5 題理解題
   - 對話場景：8~12 句對話，含角色、情境、可替換句型
   - 需產出「課程元資料」：語言、CEFR 等級(英)/JLPT 等級(日)、主題、生成日期、預估學習時間、重點

5) 自動歸檔：
   - 將每次生成的課程存成 JSON 檔案到 data/lessons/YYYY-MM-DD/lesson_{uuid}.json
   - 同時寫入 SQLite：lessons 表與 progress 表，方便查詢

6) 排程：
   - 提供一個 scheduler（APScheduler 或 cron 指引）
   - 每天早上 07:30 自動生成今日課程（若當天尚未生成）
   - 也可手動觸發生成
