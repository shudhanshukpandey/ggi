"""
Post, Comment, and Reaction Data Models with Visibility Attributes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from social_platform.privacy.enums import VisibilityLevel

@dataclass
class Post:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    author_id: str = ""
    content: str = ""
    visibility: VisibilityLevel = VisibilityLevel.PUBLIC
    media_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    reactions: dict[str, int] = field(default_factory=dict)
    comment_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Comment:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    post_id: str = ""
    author_id: str = ""
    text: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Reaction:
    post_id: str
    user_id: str
    emoji: str = "❤️"
