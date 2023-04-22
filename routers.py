from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from web_html import html
from manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()


@router.get("/")
async def get():
    return HTMLResponse(html)


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    await manager.broadcast(f"{client_id} joined the chat")
    try:
        while True:
            data = await websocket.receive_text()
            data = data.split(",")
            if data:
                await manager.broadcast(f"{data[0]}: {data[1]}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{data[0]} left the chat")


async def send_personal_message(message: str, websocket: WebSocket):
    await websocket.send_text(message)
