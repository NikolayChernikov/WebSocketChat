from fastapi import APIRouter
from starlette.responses import FileResponse

from response import UserInfoResponse
from typing import Optional
from fastapi import Body, HTTPException
from starlette.requests import Request
from validate import UserListResponse, Distance, ThunderDistance

from room import Room

router = APIRouter()


@router.get("/")
def home():
    return FileResponse("src/index.html")


@router.get("/users", response_model=UserListResponse)
async def list_users(request: Request):
    room: Optional[Room] = request.get("room")
    if room is None:
        raise HTTPException(500, detail="Global `Room` instance unavailable!")
    return {"users": room.user_list}


@router.get("/users/{user_id}", response_model=UserInfoResponse)
async def get_user_info(request: Request, user_id: str):
    room: Optional[Room] = request.get("room")
    if room is None:
        raise HTTPException(500, detail="Global `Room` instance unavailable!")
    user = room.get_user(user_id)
    if user is None:
        raise HTTPException(404, detail=f"No such user: {user_id}")
    return user


@router.post("/users/{user_id}/kick", response_model=UserListResponse)
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


@router.post("/thunder")
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
