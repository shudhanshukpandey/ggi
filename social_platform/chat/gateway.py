"""
Chat Gateway — message dispatching, read receipts, and privacy verification.
"""

from social_platform.chat.models import Message, Conversation, ChannelType
from social_platform.chat.manager import ConnectionManager
from social_platform.auth.service import AuthService
from social_platform.privacy.policy import PrivacyPolicyEngine
from social_platform.privacy.enums import VisibilityLevel, ResourceType

class ChatGateway:
    def __init__(self, auth_service: AuthService, privacy_engine: PrivacyPolicyEngine):
        self.auth_service = auth_service
        self.privacy_engine = privacy_engine
        self.connection_manager = ConnectionManager()
        self.conversations: dict[str, Conversation] = {}
        self.messages: dict[str, list[Message]] = {}

    def create_direct_chat(self, user_a_id: str, user_b_id: str) -> Conversation:
        conv = Conversation(channel_type=ChannelType.DIRECT, participants=[user_a_id, user_b_id])
        self.conversations[conv.id] = conv
        self.messages[conv.id] = []
        return conv

    def send_message(self, conversation_id: str, sender_id: str, content: str) -> Message | None:
        conv = self.conversations.get(conversation_id)
        if not conv or sender_id not in conv.participants:
            return None

        msg = Message(conversation_id=conversation_id, sender_id=sender_id, content=content, encrypted=True)
        self.messages[conversation_id].append(msg)
        return msg
