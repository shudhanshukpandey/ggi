"""
Global application settings and environment configuration.
"""

from dataclasses import dataclass, field
import os

@dataclass
class AppConfig:
    app_name: str = "Nexus Social Platform"
    environment: str = os.getenv("APP_ENV", "development")
    jwt_secret_key: str = os.getenv("JWT_SECRET", "nexus-super-secret-key-32b-length")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    webrtc_turn_server: str = "turn:turn.nexus-social.net:3478"
    webrtc_stun_server: str = "stun:stun.l.google.com:19302"
    ws_heartbeat_interval_sec: int = 30
    storage_bucket_public: str = "nexus-public-media"
    storage_bucket_vault: str = "nexus-private-vault"
    allowed_cors_origins: list[str] = field(default_factory=lambda: ["*"])

config = AppConfig()
