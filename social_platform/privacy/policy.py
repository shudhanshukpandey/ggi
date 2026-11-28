"""
Privacy Policy Engine — evaluates access control for public vs private items,
enforcing strict friendship and blocklist checks.
"""

from social_platform.privacy.enums import VisibilityLevel, ResourceType
from social_platform.auth.models import User
from social_platform.privacy.audit import AccessAuditLogger

class PrivacyPolicyEngine:
    def __init__(self, audit_logger: AccessAuditLogger | None = None):
        self.audit_logger = audit_logger or AccessAuditLogger()

    def can_view(
        self,
        viewer: User | None,
        owner: User,
        visibility: VisibilityLevel,
        resource_type: ResourceType,
        allowed_user_ids: list[str] | None = None,
    ) -> bool:
        """Evaluate if viewer is permitted to access the target resource."""
        # 1. Owner always has full access
        if viewer and viewer.id == owner.id:
            return True

        # 2. Blocked users are unconditionally denied
        if viewer and (viewer.id in owner.blocked_users or owner.id in viewer.blocked_users):
            self.audit_logger.log_denial(viewer.id, owner.id, resource_type, "blocked")
            return False

        # 3. Public items are accessible to everyone
        if visibility == VisibilityLevel.PUBLIC:
            return True

        # 4. Anonymous viewers cannot view non-public resources
        if not viewer:
            return False

        # 5. Private items are strictly restricted to owner
        if visibility == VisibilityLevel.PRIVATE:
            return False

        # 6. Friends-only items require mutual friendship
        if visibility == VisibilityLevel.FRIENDS_ONLY:
            is_friend = viewer.id in owner.friends
            if not is_friend:
                self.audit_logger.log_denial(viewer.id, owner.id, resource_type, "not_friends")
            return is_friend

        # 7. Restricted allowlist
        if visibility == VisibilityLevel.RESTRICTED:
            return bool(allowed_user_ids and viewer.id in allowed_user_ids)

        return False
