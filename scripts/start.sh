#!/bin/bash
# 大丈夫整理術 - 啟動腳本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚀 啟動大丈夫整理術..."

# 啟動資料庫
echo "📦 啟動資料庫..."
docker compose up -d db

# 等待資料庫就緒
echo "⏳ 等待資料庫就緒..."
sleep 3

# 啟動 Bot
echo "🤖 啟動 Discord Bot..."
source .venv/bin/activate
python -m src.bot.main
