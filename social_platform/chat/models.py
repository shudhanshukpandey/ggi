"""
Real-time Chat and Messaging Data Models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

class ChannelType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    COMMUNITY = "community"

@dataclass
class Message:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    conversation_id: str = ""
    sender_id: str = ""
    content: str = ""
    encrypted: bool = True
    read_by: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Conversation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    channel_type: ChannelType = ChannelType.DIRECT
    participants: list[str] = field(default_factory=list)
    name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
