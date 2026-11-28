"""
Input Sanitizer and Request Validator.
"""

import re

class InputValidator:
    @staticmethod
    def validate_username(username: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9_-]{3,24}$", username))

    @staticmethod
    def validate_email(email: str) -> bool:
        return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

    @staticmethod
    def sanitize_post_content(text: str) -> str:
        # Strip script tags and limit length
        clean = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL)
        return clean.strip()[:5000]
