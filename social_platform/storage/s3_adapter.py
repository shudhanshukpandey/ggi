"""
Public Media CDN Adapter for public posts, avatars, and cover photos.
"""

class PublicMediaCDN:
    def __init__(self, bucket_name: str = "nexus-public-media"):
        self.bucket = bucket_name

    def upload_public_asset(self, filename: str, data: bytes) -> str:
        return f"https://cdn.nexus-social.net/{self.bucket}/{filename}"
