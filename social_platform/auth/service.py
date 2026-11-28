"""
Authentication Service: user registration, password verification, and JWT issuance.
"""

import hashlib
import time
from social_platform.auth.models import User, Token

class AuthService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._users: dict[str, User] = {}

    def hash_password(self, password: str) -> str:
        return hashlib.sha256((password + self.secret_key).encode()).hexdigest()

    def register_user(self, username: str, email: str, password: str) -> User:
        pwd_hash = self.hash_password(password)
        user = User(username=username, email=email, password_hash=pwd_hash, display_name=username)
        self._users[user.id] = user
        return user

    def authenticate(self, username: str, password: str) -> User | None:
        pwd_hash = self.hash_password(password)
        for u in self._users.values():
            if u.username == username and u.password_hash == pwd_hash:
                return u
        return None

    def issue_token(self, user: User) -> Token:
        payload = f"{user.id}:{time.time()}:{self.secret_key[:8]}"
        token_str = hashlib.sha256(payload.encode()).hexdigest()
        return Token(access_token=token_str)
