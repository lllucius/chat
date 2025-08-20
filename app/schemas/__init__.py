"""Pydantic schemas package."""

from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserInDB, User, UserLogin
)
from app.schemas.chat import (
    ChatRequest, ChatResponse, StreamingChatResponse
)
from app.schemas.message import (
    MessageBase, MessageCreate, MessageUpdate, Message, MessageWithEmbedding
)
from app.schemas.conversation import (
    ConversationBase, ConversationCreate, ConversationUpdate, Conversation,
    ConversationWithMessages
)
from app.schemas.document import (
    DocumentBase, DocumentCreate, DocumentUpdate, Document, DocumentUpload
)
from app.schemas.profile import (
    ProfileBase, ProfileCreate, ProfileUpdate, Profile
)
from app.schemas.prompt import (
    PromptBase, PromptCreate, PromptUpdate, Prompt
)
from app.schemas.analytics import (
    AnalyticsBase, AnalyticsCreate, Analytics, AnalyticsSummary
)

__all__ = [
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserInDB", "User", "UserLogin",
    # Chat schemas
    "ChatRequest", "ChatResponse", "StreamingChatResponse",
    # Message schemas
    "MessageBase", "MessageCreate", "MessageUpdate", "Message", "MessageWithEmbedding",
    # Conversation schemas
    "ConversationBase", "ConversationCreate", "ConversationUpdate", "Conversation",
    "ConversationWithMessages",
    # Document schemas
    "DocumentBase", "DocumentCreate", "DocumentUpdate", "Document", "DocumentUpload",
    # Profile schemas
    "ProfileBase", "ProfileCreate", "ProfileUpdate", "Profile",
    # Prompt schemas
    "PromptBase", "PromptCreate", "PromptUpdate", "Prompt",
    # Analytics schemas
    "AnalyticsBase", "AnalyticsCreate", "Analytics", "AnalyticsSummary",
]