import time
from typing import Dict, List, Optional

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from validate import UserInfo


class Room:
    def __init__(self):
        self._users: Dict[str, WebSocket] = {}
        self._user_meta: Dict[str, UserInfo] = {}

    def __len__(self) -> int:
        return len(self._users)

    @property
    def empty(self) -> bool:
        return len(self._users) == 0

    @property
    def user_list(self) -> List[str]:
        return list(self._users)

    def add_user(self, user_id: str, websocket: WebSocket):
        if user_id in self._users:
            raise ValueError(f"User {user_id} is already in the room")
        self._users[user_id] = websocket
        self._user_meta[user_id] = UserInfo(
            user_id=user_id, connected_at=time.time(), message_count=0
        )

    async def kick_user(self, user_id: str):
        if user_id not in self._users:
            raise ValueError(f"User {user_id} is not in the room")
        await self._users[user_id].send_json(
            {
                "type": "ROOM_KICK",
                "data": {"msg": "You have been kicked from the chatroom!"},
            }
        )
        await self._users[user_id].close()

    def remove_user(self, user_id: str):
        if user_id not in self._users:
            raise ValueError(f"User {user_id} is not in the room")
        del self._users[user_id]
        del self._user_meta[user_id]

    def get_user(self, user_id: str) -> Optional[UserInfo]:
        return self._user_meta.get(user_id)

    async def whisper(self, from_user: str, to_user: str, msg: str):
        if from_user not in self._users:
            raise ValueError(f"Calling user {from_user} is not in the room")
        if to_user not in self._users:
            await self._users[from_user].send_json(
                {
                    "type": "ERROR",
                    "data": {"msg": f"User {to_user} is not in the room!"},
                }
            )
            return
        await self._users[to_user].send_json(
            {
                "type": "WHISPER",
                "data": {"from_user": from_user, "to_user": to_user, "msg": msg},
            }
        )

    async def broadcast_message(self, user_id: str, msg: str):
        self._user_meta[user_id].message_count += 1
        for websocket in self._users.values():
            await websocket.send_json(
                {"type": "MESSAGE", "data": {"user_id": user_id, "msg": msg}}
            )

    async def broadcast_user_joined(self, user_id: str):
        for websocket in self._users.values():
            await websocket.send_json({"type": "USER_JOIN", "data": user_id})

    async def broadcast_user_left(self, user_id: str):
        for websocket in self._users.values():
            await websocket.send_json({"type": "USER_LEAVE", "data": user_id})


class RoomEventMiddleware:  # pylint: disable=too-few-public-methods
    def __init__(self, app: ASGIApp):
        self._app = app
        self._room = Room()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("lifespan", "http", "websocket"):
            scope["room"] = self._room
        await self._app(scope, receive, send)
