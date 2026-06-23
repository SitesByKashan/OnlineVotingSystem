from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_connection
from ..dependencies import require_admin
from ..schemas import ElectionCreate, ElectionStatusUpdate, ElectionUpdate, MessageResponse, UserPublic
from ..websocket_manager import manager

router = APIRouter(tags=["Elections"])


@router.get("/elections")
def list_elections() -> dict:
    with get_connection() as db:
        rows = db.execute("SELECT * FROM elections ORDER BY created_at DESC").fetchall()
    return {"elections": [dict(row) for row in rows]}


@router.get("/elections/{election_id}")
def get_election(election_id: int) -> dict:
    with get_connection() as db:
        election = db.execute("SELECT * FROM elections WHERE id = ?", (election_id,)).fetchone()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found.")
    return {"election": dict(election)}


@router.post("/admin/elections")
def create_election(payload: ElectionCreate, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        cursor = db.execute(
            """
            INSERT INTO elections (title, description, start_time, end_time, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.title, payload.description, payload.start_time, payload.end_time, admin.id),
        )
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'ELECTION_CREATED', ?)",
            (admin.id, admin.email, f"Election '{payload.title}' created."),
        )
    return {"message": "Election created.", "election_id": cursor.lastrowid}


@router.put("/admin/elections/{election_id}", response_model=MessageResponse)
def update_election(election_id: int, payload: ElectionUpdate, _: UserPublic = Depends(require_admin)) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No changes supplied."}
    fields = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [election_id]
    with get_connection() as db:
        cursor = db.execute(f"UPDATE elections SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Election not found.")
    return {"message": "Election updated."}


async def _set_status(election_id: int, status: str, admin: UserPublic) -> dict:
    with get_connection() as db:
        cursor = db.execute("UPDATE elections SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, election_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Election not found.")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'ELECTION_STATUS_CHANGED', ?)",
            (admin.id, admin.email, f"Election {election_id} changed to {status}."),
        )
    await manager.broadcast(f"election:{election_id}", {"type": "ELECTION_STATUS", "status": status})
    await manager.broadcast("admin:notifications", {"type": "ELECTION_STATUS", "election_id": election_id, "status": status})
    return {"message": f"Election status changed to {status}."}


@router.post("/admin/elections/{election_id}/start")
async def start_election(election_id: int, admin: UserPublic = Depends(require_admin)) -> dict:
    return await _set_status(election_id, "ACTIVE", admin)


@router.post("/admin/elections/{election_id}/pause")
async def pause_election(election_id: int, admin: UserPublic = Depends(require_admin)) -> dict:
    return await _set_status(election_id, "PAUSED", admin)


@router.post("/admin/elections/{election_id}/close")
async def close_election(election_id: int, admin: UserPublic = Depends(require_admin)) -> dict:
    return await _set_status(election_id, "CLOSED", admin)


@router.post("/admin/elections/{election_id}/status")
async def set_election_status(
    election_id: int,
    payload: ElectionStatusUpdate,
    admin: UserPublic = Depends(require_admin),
) -> dict:
    return await _set_status(election_id, payload.status, admin)


@router.post("/admin/elections/{election_id}/publish")
async def publish_election(election_id: int, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        cursor = db.execute(
            "UPDATE elections SET status = 'PUBLISHED', result_published_at = CURRENT_TIMESTAMP WHERE id = ?",
            (election_id,),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Election not found.")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'RESULT_PUBLISHED', ?)",
            (admin.id, admin.email, f"Election {election_id} result published."),
        )
    await manager.broadcast(f"leaderboard:{election_id}", {"type": "RESULT_PUBLISHED", "election_id": election_id})
    await manager.broadcast("admin:notifications", {"type": "RESULT_PUBLISHED", "election_id": election_id})
    return {"message": "Election result published."}


@router.delete("/admin/elections/{election_id}", response_model=MessageResponse)
def delete_election(election_id: int, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        votes = db.execute("SELECT COUNT(*) FROM votes WHERE election_id = ?", (election_id,)).fetchone()[0]
        if votes:
            raise HTTPException(status_code=409, detail="Cannot delete an election that already has votes.")
        db.execute("DELETE FROM candidate_applications WHERE election_id = ?", (election_id,))
        db.execute("DELETE FROM candidates WHERE election_id = ?", (election_id,))
        cursor = db.execute("DELETE FROM elections WHERE id = ?", (election_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Election not found.")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'ELECTION_DELETED', ?)",
            (admin.id, admin.email, f"Election {election_id} deleted."),
        )
    return {"message": "Election deleted."}
