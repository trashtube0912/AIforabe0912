# 台股市場情報中心

完全由 GitHub Actions 雲端執行的自動化報告系統。

- 平日 08:15（台北時間）：開盤前市場情緒分析
- 平日 13:50：台股大盤盤後分析
- 每週三、六 19:00：股癌 Podcast 摘要
- 報告會寫入 GitHub Pages 的 docs/reports/

## 設定

在 GitHub 儲存庫的 Settings → Secrets and variables → Actions 新增：

- OPENAI_API_KEY：用來產生 AI 市場觀察及 Podcast 摘要（建議）
- PODCAST_RSS_URL：股癌的合法 Podcast RSS URL；未設定時 Podcast 工作安全略過。

並在 Settings → Actions → General 將 Workflow permissions 設為 Read and write permissions。

資料僅供資訊整理，非投資建議。
