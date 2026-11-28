"""
WebSocket Connection Manager for real-time messaging.
"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set] = {}

    def connect(self, user_id: str, socket_id: str):
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(socket_id)

    def disconnect(self, user_id: str, socket_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(socket_id)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
