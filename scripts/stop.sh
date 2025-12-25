#!/bin/bash
# 大丈夫整理術 - 停止腳本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🛑 停止大丈夫整理術..."

# 停止 Bot
echo "🤖 停止 Discord Bot..."
pkill -f "src.bot.main" 2>/dev/null || true

# 停止資料庫
echo "📦 停止資料庫..."
docker compose down

echo "✅ 已停止"
