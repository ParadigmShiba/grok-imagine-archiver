# GEMINI.md - 專案脈絡與 AI 執行任務指南

此文件為 Gemini CLI 與 AI 代理在執行 **Grok Imagine Collection** 專案時的「核心記憶錨點（Memory Anchor）」與「行為準則」。AI 在執行任何操作前，請嚴格遵守以下指示。

## 🧠 1. 專案脈絡 (Project Context)
本專案專注於 **監聽與截取使用 grok.com 的圖像生成模型時，前端與後端的 wss 的 request/response內容，將每一輪的 request (text prompt) / response (images) 儲存到本地端個別資料夾（gallery），資料夾名稱為 grok job id+timestamp，並建立一個 web ui 來展示這些圖片與 prompt**

## 🤖 2. AI 代理核心鐵則 (AI Agent Core Mandates)
1. **啟動喚醒程序 (AI Boot Sequence)**：在工作區開始新對話前，AI 必須自主讀取 `README.md`，並執行 `git log -n 5 --stat` 檢視最近 5 次的 commit，確保完美掌握最新開發脈絡。
2. **虛擬環境強制性 (Venv Mandate)**：執行任何 Python 程式碼時，**必須**使用該專案的虛擬環境 (venv)。
3. **Git 災難防範預檢 (Git Pre-flight Check)**：在執行 `git add .` 前，AI 必須確保 `.gitignore` 存在且已忽略 `venv/`, `.env`, `__pycache__/` 與大型暫存資料夾。
4. **版本控制強制性 (Git Mandate)**：修改、重構或刪除檔案後，AI 必須立即自主執行 `git status`, `git diff` 與 `git commit`。執行時**必須設定 `SafeToAutoRun: true`** 避免中斷用戶。
5. **跨語言內嵌語法驗證 (Cross-Language Embed Validation)**：撰寫動態生成或內嵌 HTML/JS/CSS 的 Python 腳本時，必須手動雙重檢查字串插值 (如 `f-strings`)，並自主驗證輸出檔案，確保無語法注入錯誤。
6. **原生 JS 動態 DOM 綁定守則 (Vanilla DOM Mutation Protocol)**：透過 `innerHTML` 替換容器內容時，**禁止**在頁面載入時綁定事件。必須在 `document.body` 或永久性父容器上實作 **動態事件委派 (Event Delegation)**。


## 🏗 3. 開發與編碼規範 (Coding Conventions)
- **環境**：Python 3.10+，撰寫乾淨的 OOP 或函數式腳本。
- **語言**：介面與 Web 端全面導入**繁體中文** (字體優先採用 Microsoft JhengHei)。
- **字串處理鐵則**：Python 生成代碼時**嚴禁**使用單行 `\n` 作為段落排版，必須依賴正規的資料結構或模板引擎處理換行。
