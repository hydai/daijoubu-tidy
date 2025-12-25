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
