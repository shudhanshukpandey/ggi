"""
Call Room Manager — tracks peer connections and call session lifecycles.
"""

class CallRoomManager:
    def __init__(self):
        self.active_rooms: dict[str, list[str]] = {}

    def register_call(self, room_id: str, participants: list[str]):
        self.active_rooms[room_id] = participants

    def close_call(self, room_id: str):
        self.active_rooms.pop(room_id, None)

    def is_user_in_call(self, user_id: str) -> bool:
        return any(user_id in p for p in self.active_rooms.values())
