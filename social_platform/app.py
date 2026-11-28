"""
Central Application Entry Point & Module Orchestrator.
Integrates Auth, Privacy, Posts, Chat, and Calls.
"""

from social_platform.config import config
from social_platform.auth.service import AuthService
from social_platform.privacy.policy import PrivacyPolicyEngine
from social_platform.posts.service import PostService
from social_platform.chat.gateway import ChatGateway
from social_platform.calls.signaling import CallSignalingEngine

class SocialMediaApp:
    def __init__(self):
        self.config = config
        self.auth_service = AuthService(secret_key=config.jwt_secret_key)
        self.privacy_engine = PrivacyPolicyEngine()
        self.post_service = PostService(privacy_engine=self.privacy_engine)
        self.chat_gateway = ChatGateway(auth_service=self.auth_service, privacy_engine=self.privacy_engine)
        self.call_signaling = CallSignalingEngine(auth_service=self.auth_service, privacy_engine=self.privacy_engine)

    def startup(self) -> dict:
        return {
            "status": "online",
            "app": self.config.app_name,
            "env": self.config.environment,
            "services": ["auth", "privacy", "posts", "chat", "calls", "storage"],
        }

app_instance = SocialMediaApp()
