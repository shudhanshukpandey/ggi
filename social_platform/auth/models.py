"""
Authentication and User Identity Models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class User:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    username: str = ""
    email: str = ""
    password_hash: str = ""
    display_name: str = ""
    avatar_url: str = ""
    bio: str = ""
    friends: list[str] = field(default_factory=list)
    blocked_users: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Session:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Token:
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400
