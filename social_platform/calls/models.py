"""
WebRTC Call Session and Participant Data Models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

class CallType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"

class CallState(str, Enum):
    RINGING = "ringing"
    CONNECTED = "connected"
    MUTED = "muted"
    ON_HOLD = "on_hold"
    ENDED = "ended"

@dataclass
class CallSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    caller_id: str = ""
    callee_id: str = ""
    call_type: CallType = CallType.VIDEO
    state: CallState = CallState.RINGING
    sdp_offer: str | None = None
    sdp_answer: str | None = None
    ice_candidates: list[dict] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None
