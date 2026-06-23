from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..database import get_connection
from ..websocket_manager import manager

router = APIRouter(tags=["WebSockets"])


async def _room_loop(room: str, websocket: WebSocket) -> None:
    await manager.connect(room, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)


@router.websocket("/ws/votes/{election_id}")
async def votes_ws(websocket: WebSocket, election_id: int) -> None:
    await manager.connect(f"votes:{election_id}", websocket)
    try:
        with get_connection() as db:
            total = db.execute("SELECT COUNT(*) FROM votes WHERE election_id = ?", (election_id,)).fetchone()[0]
        await websocket.send_json({"type": "VOTE_COUNT", "election_id": election_id, "total_votes": total})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(f"votes:{election_id}", websocket)


@router.websocket("/ws/leaderboard/{election_id}")
async def leaderboard_ws(websocket: WebSocket, election_id: int) -> None:
    await manager.connect(f"leaderboard:{election_id}", websocket)
    try:
        with get_connection() as db:
            rows = db.execute(
                """
                SELECT candidates.id, candidates.name, candidates.party, COUNT(votes.id) AS votes
                FROM candidates
                LEFT JOIN votes ON votes.candidate_id = candidates.id
                WHERE candidates.election_id = ?
                GROUP BY candidates.id
                ORDER BY votes DESC
                """,
                (election_id,),
            ).fetchall()
        await websocket.send_json({"type": "LEADERBOARD", "results": [dict(row) for row in rows]})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(f"leaderboard:{election_id}", websocket)


@router.websocket("/ws/admin/notifications")
async def admin_notifications_ws(websocket: WebSocket) -> None:
    await manager.connect("admin:notifications", websocket)
    try:
        with get_connection() as db:
            rows = db.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
        await websocket.send_json({"type": "NOTIFICATIONS", "notifications": [dict(row) for row in rows]})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("admin:notifications", websocket)


@router.websocket("/ws/security-alerts")
async def security_alerts_ws(websocket: WebSocket) -> None:
    await manager.connect("security:alerts", websocket)
    try:
        with get_connection() as db:
            rows = db.execute("SELECT * FROM ai_alerts ORDER BY severity DESC, created_at DESC LIMIT 10").fetchall()
        await websocket.send_json({"type": "SECURITY_ALERTS", "alerts": [dict(row) for row in rows]})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("security:alerts", websocket)
