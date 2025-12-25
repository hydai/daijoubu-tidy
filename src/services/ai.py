import logging

from openai import AsyncOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI operations using OpenAI API."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not set, skipping embedding generation")
            return None

        try:
            response = await self.client.embeddings.create(
                model=settings.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def classify_content(self, content: str) -> str | None:
        """Classify content into a category using AI."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not set, skipping classification")
            return None

        try:
            response = await self.client.chat.completions.create(
                model=settings.classification_model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a content classifier. Classify the given content into ONE of these categories:
- work: Work-related content, meetings, projects
- personal: Personal notes, diary, thoughts
- learning: Educational content, tutorials, courses
- reference: Links, documentation, resources
- ideas: Ideas, brainstorming, inspiration
- tasks: Todo items, reminders, action items
- finance: Money, budgets, expenses
- health: Health, fitness, wellness
- entertainment: Movies, games, hobbies
- other: Anything that doesn't fit above

Reply with ONLY the category name, nothing else.""",
                    },
                    {"role": "user", "content": content},
                ],
                max_tokens=20,
                temperature=0.3,
            )

            category = response.choices[0].message.content.strip().lower()

            # Validate category
            valid_categories = [
                "work",
                "personal",
                "learning",
                "reference",
                "ideas",
                "tasks",
                "finance",
                "health",
                "entertainment",
                "other",
            ]
            if category in valid_categories:
                return category
            return "other"

        except Exception as e:
            logger.error(f"Error classifying content: {e}")
            return None

    async def generate_summary(self, items: list) -> str:
        """Generate a summary of items."""
        if not settings.openai_api_key:
            return "Summary generation requires OpenAI API key."

        if not items:
            return "No items to summarize."

        # Prepare content for summarization
        content_list = []
        for item in items[:20]:  # Limit to 20 items
            content_list.append(f"- {item.content[:200]}")

        combined_content = "\n".join(content_list)

        try:
            response = await self.client.chat.completions.create(
                model=settings.summary_model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant that summarizes a collection of notes and information.
Provide a concise summary that:
1. Highlights key themes and topics
2. Notes any important items or deadlines
3. Groups related items together
4. Uses clear, bullet-point format

Keep the summary under 300 words.""",
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize these items:\n\n{combined_content}",
                    },
                ],
                max_tokens=500,
                temperature=0.5,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {e}"

    async def analyze_image_for_declutter(self, image_url: str) -> dict:
        """Analyze an image and provide decluttering advice for each item."""
        if not settings.openai_api_key:
            return {
                "error": "需要 OpenAI API Key 才能分析圖片",
            }

        try:
            response = await self.client.chat.completions.create(
                model=settings.vision_model,
                messages=[
                    {
                        "role": "system",
                        "content": """你是一位專業的斷捨離顧問，專門幫助人們整理物品、簡化生活。

分析用戶上傳的照片，識別照片中的【每一個獨立物品】，並為每個物品分別提供斷捨離建議。

## 斷捨離三原則
1. **斷** - 斷絕不需要的東西進入生活
2. **捨** - 捨棄堆放在家裡沒用的東西
3. **離** - 脫離對物品的執著

## 評估標準
- 實用性：這個物品有實際用途嗎？
- 使用頻率：最近一年內用過嗎？
- 情感價值：有重要的紀念意義嗎？
- 替代性：可以用其他東西替代嗎？
- 狀態：物品的狀況如何？

## 重要：回應格式
你必須以 JSON 格式回應，包含一個 items 陣列，每個物品一個項目。
請確保回應是有效的 JSON 格式，不要包含任何其他文字。

```json
{
  "items": [
    {
      "name": "物品名稱（簡短，如：電風扇、紙箱、衣服）",
      "decision": "keep 或 consider 或 discard",
      "reason": "建議理由（1-2句話）",
      "action": "具體行動建議"
    }
  ]
}
```

decision 對應：
- keep = 🟢 保留
- consider = 🟡 考慮
- discard = 🔴 捨棄

請為照片中每個可識別的獨立物品建立一個項目。如果是一堆相同的東西（如一疊紙），算作一個項目。""",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "請分析這張照片中的每個物品，為每個物品分別給我斷捨離的建議。請以 JSON 格式回應。",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    },
                ],
                max_tokens=2000,
                temperature=0.7,
            )

            content = response.choices[0].message.content.strip()

            # 嘗試解析 JSON
            import json
            import re

            # 移除可能的 markdown 代碼塊標記
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

            try:
                data = json.loads(content)
                items = data.get("items", [])

                if not items:
                    return {
                        "error": "無法識別照片中的物品",
                    }

                return {
                    "success": True,
                    "items": items,
                }
            except json.JSONDecodeError:
                # 如果 JSON 解析失敗，嘗試舊的單一分析格式
                logger.warning(f"JSON 解析失敗，使用原始回應: {content[:100]}...")
                return {
                    "success": True,
                    "items": [{
                        "name": "未知物品",
                        "decision": "consider",
                        "reason": content[:200],
                        "action": "請重新拍攝更清晰的照片",
                    }],
                }

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                "error": f"分析圖片時發生錯誤：{e}",
            }
