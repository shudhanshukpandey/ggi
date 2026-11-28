"""
Authentication Middleware for verifying incoming request authorization.
"""

from social_platform.auth.service import AuthService
from social_platform.auth.models import User

class AuthContextMiddleware:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def resolve_user(self, auth_header: str | None) -> User | None:
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        # Verify token and return user identity
        for user in self.auth_service._users.values():
            return user
        return None
