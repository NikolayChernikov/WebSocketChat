import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel
from starlette.endpoints import WebSocketEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket


app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]
)
app.debug = True

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class UserInfo(BaseModel):
    user_id: str
    connected_at: float
    message_count: int


class Room:
    def __init__(self):
        log.info("Creating new empty room")
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
        log.info("Adding user %s to room", user_id)
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
        log.info("Kicking user %s from room", user_id)
        await self._users[user_id].close()

    def remove_user(self, user_id: str):
        if user_id not in self._users:
            raise ValueError(f"User {user_id} is not in the room")
        log.info("Removing user %s from room", user_id)
        del self._users[user_id]
        del self._user_meta[user_id]

    def get_user(self, user_id: str) -> Optional[UserInfo]:
        return self._user_meta.get(user_id)

    async def whisper(self, from_user: str, to_user: str, msg: str):
        if from_user not in self._users:
            raise ValueError(f"Calling user {from_user} is not in the room")
        log.info("User %s messaging user %s -> %s", from_user, to_user, msg)
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


app.add_middleware(RoomEventMiddleware)


@app.get("/")
def home():
    return FileResponse("index.html")


class UserListResponse(BaseModel):
    users: List[str]


@app.get("/users", response_model=UserListResponse)
async def list_users(request: Request):
    room: Optional[Room] = request.get("room")
    if room is None:
        raise HTTPException(500, detail="Global `Room` instance unavailable!")
    return {"users": room.user_list}


class UserInfoResponse(UserInfo):
    """Response model for /users/:user_id endpoint.
    """


@app.get("/users/{user_id}", response_model=UserInfoResponse)
async def get_user_info(request: Request, user_id: str):
    room: Optional[Room] = request.get("room")
    if room is None:
        raise HTTPException(500, detail="Global `Room` instance unavailable!")
    user = room.get_user(user_id)
    if user is None:
        raise HTTPException(404, detail=f"No such user: {user_id}")
    return user


@app.post("/users/{user_id}/kick", response_model=UserListResponse)
async def kick_user(request: Request, user_id: str):
    """List all users connected to the room.
    """
    room: Optional[Room] = request.get("room")
    if room is None:
        raise HTTPException(500, detail="Global `Room` instance unavailable!")
    try:
        await room.kick_user(user_id)
    except ValueError:
        raise HTTPException(404, detail=f"No such user: {user_id}")


class Distance(str, Enum):
    """Distance classes for the /thunder endpoint.
    """

    Near = "near"
    Far = "far"
    Extreme = "extreme"


class ThunderDistance(BaseModel):
    category: Distance


@app.post("/thunder")
async def thunder(request: Request, distance: ThunderDistance = Body(...)):
    room: Optional[Room] = request.get("room")
    if room is None:
        raise HTTPException(500, detail="Global `Room` instance unavailable!")
    if distance.category == Distance.Near:
        await room.broadcast_message("server", "Thunder booms overhead")
    elif distance.category == Distance.Far:
        await room.broadcast_message("server", "Thunder rumbles in the distance")
    else:
        await room.broadcast_message("server", "You feel a faint tremor")


@app.websocket_route("/ws", name="ws")
class RoomLive(WebSocketEndpoint):
    encoding: str = "text"
    session_name: str = ""
    count: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room: Optional[Room] = None
        self.user_id: Optional[str] = None

    @classmethod
    def get_next_user_id(cls):
        user_id: str = f"user_{cls.count}"
        cls.count += 1
        return user_id

    async def on_connect(self, websocket):
        log.info("Connecting new user...")
        room: Optional[Room] = self.scope.get("room")
        if room is None:
            raise RuntimeError(f"Global `Room` instance unavailable!")
        self.room = room
        self.user_id = self.get_next_user_id()
        await websocket.accept()
        await websocket.send_json(
            {"type": "ROOM_JOIN", "data": {"user_id": self.user_id}}
        )
        await self.room.broadcast_user_joined(self.user_id)
        self.room.add_user(self.user_id, websocket)

    async def on_disconnect(self, _websocket: WebSocket, _close_code: int):
        if self.user_id is None:
            raise RuntimeError(
                "RoomLive.on_disconnect() called without a valid user_id"
            )
        self.room.remove_user(self.user_id)
        await self.room.broadcast_user_left(self.user_id)

    async def on_receive(self, _websocket: WebSocket, msg: Any):
        if self.user_id is None:
            raise RuntimeError("RoomLive.on_receive() called without a valid user_id")
        if not isinstance(msg, str):
            raise ValueError(f"RoomLive.on_receive() passed unhandleable data: {msg}")
        await self.room.broadcast_message(self.user_id, msg)