# 大丈夫整理術

AI 驅動的個人資訊整理助手 Discord Bot，幫助你收集、分類、搜尋散落各處的數位資訊。

## 功能特色

### 資訊收集
- **文字儲存**：快速保存任何文字內容
- **URL 擷取**：自動抓取網頁標題與描述
- **手動標籤**：自訂標籤整理資訊

### AI 智慧功能
- **自動分類**：使用 GPT 自動將內容分類（工作、學習、個人等）
- **語意搜尋**：透過 pgvector 進行自然語言搜尋
- **智慧摘要**：產生每日/每週 AI 摘要

### 斷捨離助手
- **物品分析**：上傳物品照片，AI 提供斷捨離建議
- **任務追蹤**：自動建立待處理任務，可跨裝置同步
- **進度管理**：標記完成、略過或刪除任務

## 系統需求

- Python 3.12+
- Docker & Docker Compose
- Discord Bot Token
- OpenAI API Key

## 快速開始

### 1. 複製專案

```bash
git clone https://github.com/hydai/daijoubu-tidy.git
cd daijoubu-tidy
```

### 2. 建立 Discord Bot

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 點擊 **New Application**，輸入名稱（如「大丈夫整理術」）
3. 左側選單點擊 **Bot**
4. 點擊 **Reset Token** 取得 Bot Token（請妥善保存）
5. 開啟以下選項：
   - **Message Content Intent**（需要讀取訊息內容）
6. 左側選單點擊 **OAuth2** → **URL Generator**
7. Scopes 勾選：`bot`, `applications.commands`
8. Bot Permissions 勾選：
   - Send Messages
   - Read Message History
   - Use Slash Commands
   - Add Reactions
   - Embed Links
   - Attach Files
9. 複製產生的 URL，在瀏覽器開啟並邀請 Bot 至你的 Server

### 3. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```env
# Application
APP_ENV=development

# Database（使用預設值即可）
DATABASE_URL=postgresql+asyncpg://daijoubu:dev_password@localhost:5432/daijoubu

# Discord
DISCORD_BOT_TOKEN=你的-bot-token
DISCORD_GUILD_ID=你的-server-id  # 可選，加快指令同步

# OpenAI
OPENAI_API_KEY=你的-openai-api-key
```

> **取得 Guild ID**：在 Discord 設定中開啟「開發者模式」，右鍵點擊 Server → 複製 ID

### 4. 安裝與啟動

**使用 uv（推薦）：**

```bash
# 建立虛擬環境並安裝依賴
uv venv --python 3.12
uv pip install -e ".[dev]"

# 啟動（包含資料庫）
make start
```

**或使用傳統 pip：**

```bash
# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -e ".[dev]"

# 啟動資料庫
docker compose up -d db

# 執行資料庫遷移
alembic upgrade head

# 啟動 Bot
python -m src.bot.main
```

### 5. 驗證安裝

Bot 上線後，在 Discord 輸入 `/help` 應該能看到指令列表。

## 指令說明

### 資訊收集

| 指令 | 說明 |
|------|------|
| `/save <內容>` | 儲存文字內容 |
| `/save-url <網址>` | 儲存網址（自動擷取標題） |
| `/tag <編號> <標籤>` | 為項目加標籤 |
| `/list [分類]` | 列出已儲存項目 |
| `/delete <編號>` | 刪除項目 |

### 搜尋與分析

| 指令 | 說明 |
|------|------|
| `/search <關鍵字>` | 語意搜尋 |
| `/find <關鍵字>` | 關鍵字搜尋 |
| `/summary [daily/weekly]` | AI 摘要 |
| `/stats` | 使用統計 |
| `/export [json/csv]` | 匯出資料 |

### 斷捨離功能

| 指令 | 說明 |
|------|------|
| `/declutter` | 上傳物品照片，獲得斷捨離建議 |
| `/declutter-help` | 斷捨離功能說明 |
| `/tasks [狀態]` | 查看任務清單 |
| `/task-view <編號>` | 查看任務詳情 |
| `/task-done <編號>` | 標記任務完成 |
| `/task-dismiss <編號>` | 略過任務 |
| `/task-delete <編號>` | 刪除任務 |

## 常用指令

```bash
make start       # 啟動 Bot（含資料庫）
make stop        # 停止 Bot 和資料庫
make run         # 只啟動 Bot（不含資料庫）
make test        # 執行測試
make lint        # 程式碼檢查
make format      # 格式化程式碼
make db-upgrade  # 執行資料庫遷移
```

## 技術架構

| 層級 | 技術 |
|------|------|
| Interface | Discord Bot (discord.py) |
| Backend | Python 3.12 + SQLAlchemy (async) |
| Database | PostgreSQL 16 + pgvector |
| AI | OpenAI API (GPT-4.1, Embeddings) |
| Container | Docker Compose |

### AI 模型配置

| 功能 | 模型 | 用途 |
|------|------|------|
| 分類 | gpt-4.1-nano | 內容自動分類 |
| 摘要 | gpt-4.1-mini | 產生摘要報告 |
| 圖片分析 | gpt-4.1-mini | 斷捨離物品分析 |
| Embedding | text-embedding-3-small | 語意搜尋向量 |

## 專案結構

```
daijoubu-tidy/
├── src/
│   ├── bot/                 # Discord Bot
│   │   ├── main.py          # 入口點
│   │   └── cogs/            # 指令模組
│   ├── core/                # 核心設定
│   │   ├── config.py        # 環境變數
│   │   └── database.py      # 資料庫連線
│   ├── models/              # SQLAlchemy 模型
│   ├── services/            # 業務邏輯
│   └── schemas/             # Pydantic 結構
├── alembic/                 # 資料庫遷移
├── scripts/                 # 啟動腳本
├── docker-compose.yml
└── pyproject.toml
```

## 疑難排解

### Bot 無法啟動

1. 確認 `.env` 中的 `DISCORD_BOT_TOKEN` 正確
2. 確認已開啟 **Message Content Intent**
3. 檢查資料庫是否正常運作：`docker compose ps`

### 指令沒有出現

1. 等待幾分鐘，全域指令同步需要時間
2. 設定 `DISCORD_GUILD_ID` 可加快同步（僅限該 Server）
3. 重新啟動 Bot

### OpenAI API 錯誤

1. 確認 `OPENAI_API_KEY` 正確且有效
2. 確認 API 額度充足
3. 檢查網路連線

### 資料庫連線失敗

```bash
# 確認 Docker 容器運作中
docker compose ps

# 重新啟動資料庫
docker compose down
docker compose up -d db

# 等待資料庫就緒後再啟動 Bot
sleep 5
make run
```

## 授權

MIT License
