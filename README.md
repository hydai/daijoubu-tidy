# 大丈夫整理術

AI 驅動的斷捨離助手 Discord Bot，幫助你分析物品、做出取捨決定，並追蹤整理進度。

## 功能特色

### 斷捨離分析
- **多物品識別**：上傳照片，AI 自動識別每個物品並分別分析
- **智慧建議**：根據實用性、使用頻率、情感價值等標準給出建議
- **三種決定**：🟢 保留 / 🟡 考慮 / 🔴 捨棄

### 任務追蹤
- **自動建立任務**：分析後自動為每個物品建立獨立任務
- **互動式操作**：點擊數字表情快速標記完成
- **跨裝置同步**：任務儲存在資料庫，任何設備都能查看

### 進度統計
- **完成率追蹤**：視覺化進度條顯示整理進度
- **成果報告**：產生週/月斷捨離成果摘要
- **匯出記錄**：支援 JSON/CSV 格式匯出

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
2. 點擊 **New Application**，輸入名稱
3. 左側選單點擊 **Bot** → **Reset Token** 取得 Token
4. 開啟 **Message Content Intent**
5. **OAuth2** → **URL Generator**：
   - Scopes：`bot`, `applications.commands`
   - Permissions：Send Messages, Read Message History, Use Slash Commands, Add Reactions, Embed Links, Attach Files
6. 用產生的 URL 邀請 Bot 至你的 Server

### 3. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`：

```env
DISCORD_BOT_TOKEN=你的-bot-token
DISCORD_GUILD_ID=你的-server-id  # 可選
OPENAI_API_KEY=你的-openai-api-key
```

### 4. 安裝與啟動

```bash
# 使用 uv（推薦）
uv venv --python 3.12
uv pip install -e ".[dev]"
make start

# 或使用 pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d db
alembic upgrade head
python -m src.bot.main
```

## 指令說明

### 斷捨離分析

| 指令 | 說明 |
|------|------|
| `/declutter` | 上傳物品照片，AI 分析並建立任務 |
| `/declutter-help` | 查看功能說明 |

### 任務管理

| 指令 | 說明 |
|------|------|
| `/tasks` | 查看任務清單（點擊數字表情可快速標記完成） |
| `/task-view <編號>` | 查看任務詳情 |
| `/task-done <編號>` | 標記任務完成 |
| `/task-dismiss <編號>` | 略過任務 |
| `/task-delete <編號>` | 刪除任務 |

### 統計與報告

| 指令 | 說明 |
|------|------|
| `/stats` | 查看斷捨離統計（完成率、任務數等） |
| `/summary` | 產生斷捨離成果報告 |
| `/export` | 匯出記錄（JSON/CSV） |

## 常用指令

```bash
make start       # 啟動 Bot（含資料庫）
make stop        # 停止 Bot 和資料庫
make run         # 只啟動 Bot
```

## 技術架構

| 層級 | 技術 |
|------|------|
| Interface | Discord Bot (discord.py) |
| Backend | Python 3.12 + SQLAlchemy (async) |
| Database | PostgreSQL 16 |
| AI | OpenAI API (GPT-4.1-mini) |

## 授權

MIT License
