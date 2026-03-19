from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, ConversationStatus


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, conversation_id: str, status: ConversationStatus) -> None:
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation '{conversation_id}' not found — cannot update status")
        conversation.status = status.value
        await self._session.flush()
