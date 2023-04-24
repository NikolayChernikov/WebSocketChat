import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from room import RoomEventMiddleware
from fastapi_router import router as f_router
from websocket_router import router as w_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]
)
app.debug = True

app.add_middleware(RoomEventMiddleware)
app.include_router(f_router)
app.include_router(w_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", reload=True)
