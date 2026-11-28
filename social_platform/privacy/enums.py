"""
Privacy Enumerations: Visibility levels and protected resource categories.
"""

from enum import Enum

class VisibilityLevel(str, Enum):
    PUBLIC = "public"           # Visible to everyone across the network
    FRIENDS_ONLY = "friends"    # Visible only to mutual friends
    RESTRICTED = "restricted"  # Visible to custom allowlist
    PRIVATE = "private"        # Visible only to owner / author

class ResourceType(str, Enum):
    POST = "post"
    STORY = "story"
    CHANNEL = "channel"
    CALL = "call"
    PROFILE_FIELD = "profile_field"
    MEDIA_ITEM = "media_item"
