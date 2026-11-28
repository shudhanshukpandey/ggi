"""
Post Service — Feed generation, content publishing, and strict privacy filtering.
"""

from social_platform.posts.models import Post, Comment
from social_platform.auth.models import User
from social_platform.privacy.enums import VisibilityLevel, ResourceType
from social_platform.privacy.policy import PrivacyPolicyEngine

class PostService:
    def __init__(self, privacy_engine: PrivacyPolicyEngine):
        self.privacy_engine = privacy_engine
        self._posts: dict[str, Post] = {}
        self._comments: dict[str, list[Comment]] = {}

    def create_post(
        self,
        author: User,
        content: str,
        visibility: VisibilityLevel = VisibilityLevel.PUBLIC,
        media_urls: list[str] | None = None,
    ) -> Post:
        post = Post(
            author_id=author.id,
            content=content,
            visibility=visibility,
            media_urls=media_urls or [],
        )
        self._posts[post.id] = post
        return post

    def get_post_for_viewer(self, post_id: str, viewer: User | None, author: User) -> Post | None:
        post = self._posts.get(post_id)
        if not post:
            return None
        # Enforce privacy check: prevent private post leakage
        if not self.privacy_engine.can_view(viewer, author, post.visibility, ResourceType.POST):
            return None
        return post

    def get_feed_for_viewer(self, viewer: User | None, author_registry: dict[str, User]) -> list[Post]:
        """Generate feed ensuring private items do not leak into unauthorized view."""
        visible_posts = []
        for post in sorted(self._posts.values(), key=lambda p: p.created_at, reverse=True):
            author = author_registry.get(post.author_id)
            if author and self.privacy_engine.can_view(viewer, author, post.visibility, ResourceType.POST):
                visible_posts.append(post)
        return visible_posts
