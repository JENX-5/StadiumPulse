from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.websockets.manager import ws_manager
from app.core.config import get_settings
from app.core.security import JWTError, decode_access_token

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(default=None)):
    """WebSocket endpoint for clients to receive realtime operational updates.

    The live feed carries every incident, risk score, and resource
    assignment for the venue, so it must not be reachable without a valid
    session. Browsers can't attach an `Authorization` header to a WebSocket
    handshake, so the JWT is passed as a `?token=` query param instead (the
    frontend attaches it in `services/websocket.ts`) and validated here
    before the connection is accepted.
    """
    if not token:
        await websocket.close(code=1008)  # policy violation
        return
    try:
        decode_access_token(token, get_settings())
    except JWTError:
        await websocket.close(code=1008)
        return

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
