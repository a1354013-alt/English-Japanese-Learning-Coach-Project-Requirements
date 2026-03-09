# 🧠 English+Japanese Learning Coach (工業級最終版)

這是一個功能強大、架構先進的智慧語言學習平台，結合了 AI 課程生成、遊戲化進度系統、SRS 間隔複習、RAG 個人化學習與現代化的前端視覺設計。

## 🚀 專案特色

| 類別 | 核心功能 | 說明 |
| :--- | :--- | :--- |
| **系統穩定性** | **多級 Fallback** | 課程生成失敗時，自動切換模型或使用規則模板，確保系統「不怕出事」。**任務歷史追蹤**。 |
| **智慧調度** | **MoE 與動態選擇** | 根據使用者等級、任務長度、系統負載，智慧選擇 Ollama 模型，平衡成本與品質。 |
| **學習效果** | **錯誤類型分析** | 追蹤拼字、文法、詞彙錯誤分佈，提供「可證明」的學習效果證據。**學前/學後測驗**。 |
| **產品化** | **新手引導與疲勞偵測** | 第一次使用引導設定，並在正確率下降時自動提示休息或切換難度。**難度模式切換**。 |
| **遊戲化** | **RPG 成長系統** | 經驗值 (XP)、等級、成就勳章、單字卡牌收集。 |
| **個人化** | **個人化 RAG** | 支援上傳 TXT 文章，AI 根據興趣生成課程。 |
| **互動性** | **多樣化練習** | 支援克漏字、句子重組、聽寫介面。 |
| **工具性** | **Excel 匯入/PDF 匯出** | 支援批次匯入單字與課程匯出。 |

## 🛠️ 技術棧

*   **前端**：Vue 3 + Vite + TypeScript + TailwindCSS + PrimeVue + ECharts
*   **後端**：Python 3.11 + FastAPI + Uvicorn
*   **資料庫**：SQLite (資料持久化) + Redis (快取) + ChromaDB (向量資料庫)
*   **AI**：Ollama (本地 LLM)

## 📦 快速啟動指南

### 1. 環境準備

1.  **安裝 Ollama**：請確保您的系統已安裝 Ollama，並啟動服務。
2.  **下載模型**：建議下載至少兩個模型以支援多模型協作 (MoE)：
    ```bash
    ollama pull llama2:13b
    ollama pull llama3:8b
    ```
3.  **安裝 Node.js 依賴**：
    ```bash
    cd language-coach/frontend
    pnpm install
    ```
4.  **安裝 Python 依賴**：
    ```bash
    cd language-coach/backend
    sudo pip3 install -r requirements.txt pandas openpyxl
    ```

### 2. 配置環境變數

在 `language-coach/backend/.env` 中配置：

```ini
# Ollama 配置
OLLAMA_URL=http://localhost:11434
MODEL_NAME=llama2:13b        # 預設課程生成模型
SMALL_MODEL_NAME=llama3:8b   # 用於單字/簡單任務的輔助模型

# 資料庫與快取
DB_PATH=../data/language_coach.db
REDIS_URL=redis://localhost:6379/0

# 排程器配置
AUTO_GENERATE_TIME=07:30     # 每日自動生成課程時間
TIMEZONE=Asia/Taipei

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. 啟動專案

使用提供的啟動腳本，它們會自動處理依賴和資料庫初始化。

1.  **啟動後端 (終端機 1)**：
    ```bash
    cd language-coach
    ./start_backend.sh
    ```
2.  **啟動前端 (終端機 2)**：
    ```bash
    cd language-coach
    ./start_frontend.sh
    ```

### 4. 訪問應用

在瀏覽器中打開：`http://localhost:5173`

## ⚙️ API 端點 (新增 Excel 匯入)

| 方法 | 路徑 | 說明 |
| :--- | :--- | :--- |
| `POST` | `/api/import/excel` | **新增**：從 Excel 匯入單字到卡牌收集冊。 |
| `POST` | `/api/rag/upload` | 上傳 TXT 文件作為 RAG 學習素材。 |
| `POST` | `/api/generate/lesson` | 依進度生成新課程 (含 Fallback/MoE 邏輯)。 |
| `GET` | `/api/tasks` | **新增**：獲取課程生成任務歷史與狀態追蹤。 |
| `POST` | `/api/onboard` | **新增**：新手引導流程，設定初始等級與模式。 |
| `GET` | `/api/lessons` | 查詢課程歸檔。 |
| `POST` | `/api/review` | 提交練習題答案，觸發 XP、SRS 與錯誤類型分析。 |
| `GET` | `/api/progress` | 獲取使用者進度、RPG 統計與疲勞偵測狀態。 |

## 📝 Excel 匯入格式

Excel 檔案（.xlsx 或 .xls）必須包含以下欄位：

| 欄位名稱 | 必填 | 說明 |
| :--- | :--- | :--- |
| `word` | 是 | 單字或詞彙 |
| `definition` | 是 | 中文定義 |
| `reading` | 否 | 假名或音標 |
| `example` | 否 | 例句 |
| `example_translation` | 否 | 例句翻譯 |

---
*此文檔由 Manus AI 生成並維護。*
