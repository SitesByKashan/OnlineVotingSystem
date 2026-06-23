from __future__ import annotations

import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms[room].append(websocket)

    def disconnect(self, room: str, websocket: WebSocket) -> None:
        if websocket in self.rooms.get(room, []):
            self.rooms[room].remove(websocket)

    async def broadcast(self, room: str, payload: dict) -> None:
        stale: list[WebSocket] = []
        message = json.dumps(payload)
        for websocket in self.rooms.get(room, []):
            try:
                await websocket.send_text(message)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(room, websocket)


manager = ConnectionManager()
