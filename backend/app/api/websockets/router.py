from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websockets.manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for clients to receive realtime operational updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # We expect the client to keep the connection alive (e.g. by pinging).
            # The backend will push data to the client using ws_manager.broadcast()
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
