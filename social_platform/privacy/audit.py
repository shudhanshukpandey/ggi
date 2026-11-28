"""
Access Audit Logger for privacy violation tracking and telemetry.
"""

from datetime import datetime, timezone
from social_platform.privacy.enums import ResourceType

class AccessAuditLogger:
    def __init__(self):
        self.events: list[dict] = []

    def log_denial(self, viewer_id: str, owner_id: str, resource_type: ResourceType, reason: str):
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "viewer_id": viewer_id,
            "owner_id": owner_id,
            "resource": resource_type.value,
            "reason": reason,
        })
