"""
Post API Router — HTTP endpoints for creating posts and fetching public/private feeds.
"""

from social_platform.posts.service import PostService
from social_platform.auth.models import User
from social_platform.privacy.enums import VisibilityLevel

class PostRouter:
    def __init__(self, post_service: PostService):
        self.post_service = post_service

    def handle_create(self, author: User, payload: dict) -> dict:
        visibility = VisibilityLevel(payload.get("visibility", "public"))
        post = self.post_service.create_post(
            author=author,
            content=payload.get("content", ""),
            visibility=visibility,
            media_urls=payload.get("media_urls", []),
        )
        return {"status": "created", "post_id": post.id, "visibility": post.visibility.value}

    def handle_get_feed(self, viewer: User | None, author_registry: dict[str, User]) -> list[dict]:
        posts = self.post_service.get_feed_for_viewer(viewer, author_registry)
        return [
            {
                "id": p.id,
                "author_id": p.author_id,
                "content": p.content,
                "visibility": p.visibility.value,
                "created_at": p.created_at,
            }
            for p in posts
        ]
