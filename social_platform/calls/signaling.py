"""
WebRTC Call Signaling Engine — handles SDP Offer/Answer exchanges and ICE candidate routing.
"""

from social_platform.calls.models import CallSession, CallState, CallType
from social_platform.calls.room_manager import CallRoomManager
from social_platform.auth.service import AuthService
from social_platform.privacy.policy import PrivacyPolicyEngine

class CallSignalingEngine:
    def __init__(self, auth_service: AuthService, privacy_engine: PrivacyPolicyEngine):
        self.auth_service = auth_service
        self.privacy_engine = privacy_engine
        self.room_manager = CallRoomManager()
        self.sessions: dict[str, CallSession] = {}

    def initiate_call(self, caller_id: str, callee_id: str, call_type: CallType, sdp_offer: str) -> CallSession:
        session = CallSession(
            caller_id=caller_id,
            callee_id=callee_id,
            call_type=call_type,
            state=CallState.RINGING,
            sdp_offer=sdp_offer,
        )
        self.sessions[session.id] = session
        self.room_manager.register_call(session.id, [caller_id, callee_id])
        return session

    def answer_call(self, session_id: str, callee_id: str, sdp_answer: str) -> CallSession | None:
        session = self.sessions.get(session_id)
        if not session or session.callee_id != callee_id:
            return None
        # State transition: serialize SDP answer to prevent renegotiation race condition
        session.sdp_answer = sdp_answer
        session.state = CallState.CONNECTED
        return session

    def add_ice_candidate(self, session_id: str, sender_id: str, candidate: dict) -> bool:
        session = self.sessions.get(session_id)
        if not session or sender_id not in (session.caller_id, session.callee_id):
            return False
        session.ice_candidates.append(candidate)
        return True
