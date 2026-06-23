from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_connection
from ..dependencies import require_admin, require_super_admin
from ..schemas import AlertResolveRequest, AdminRoleUpdate, BlockUserRequest, MessageResponse, NotificationCreate, UserPublic
from ..websocket_manager import manager

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
@router.get("/stats")
def dashboard(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        verified = db.execute("SELECT COUNT(*) FROM users WHERE is_email_verified = 1").fetchone()[0]
        pending = db.execute("SELECT COUNT(*) FROM users WHERE is_email_verified = 0").fetchone()[0]
        votes = db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        results = db.execute(
            """
            SELECT
                candidates.id,
                candidates.election_id,
                candidates.name,
                candidates.party,
                candidates.manifesto,
                candidates.image_url,
                COUNT(votes.id) AS votes
            FROM candidates
            LEFT JOIN votes ON votes.candidate_id = candidates.id
            GROUP BY candidates.id
            ORDER BY votes DESC
            """
        ).fetchall()
        logs = db.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 20").fetchall()
    return {
        "totals": {
            "users": users,
            "verified_users": verified,
            "pending_verification": pending,
            "votes": votes,
            "turnout_percent": round((votes / verified) * 100, 2) if verified else 0,
        },
        "results": [dict(row) for row in results],
        "audit_logs": [dict(row) for row in logs],
    }


@router.get("/users")
def users(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT users.id, users.full_name, users.email, users.role, users.is_email_verified AS is_verified,
                   users.is_blocked, users.created_at, votes.receipt_code
            FROM users
            LEFT JOIN votes ON votes.user_id = users.id
            ORDER BY users.created_at DESC
            """
        ).fetchall()
    return {"users": [dict(row) for row in rows]}


@router.put("/users/{user_id}/block", response_model=MessageResponse)
def block_user(user_id: int, payload: BlockUserRequest, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        db.execute("UPDATE users SET is_blocked = ? WHERE id = ?", (int(payload.is_blocked), user_id))
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'USER_BLOCK_UPDATED', ?)",
            (admin.id, admin.email, f"User {user_id} blocked={payload.is_blocked}."),
        )
    return {"message": "User block status updated."}


@router.put("/users/{user_id}/role", response_model=MessageResponse)
def update_role(user_id: int, payload: AdminRoleUpdate, admin: UserPublic = Depends(require_super_admin)) -> dict:
    with get_connection() as db:
        db.execute("UPDATE users SET role = ? WHERE id = ?", (payload.role, user_id))
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'USER_ROLE_UPDATED', ?)",
            (admin.id, admin.email, f"User {user_id} role changed to {payload.role}."),
        )
    return {"message": "User role updated."}


@router.get("/analytics")
def analytics(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        elections = db.execute(
            """
            SELECT elections.id, elections.title, elections.status, COUNT(votes.id) AS votes
            FROM elections
            LEFT JOIN votes ON votes.election_id = elections.id
            GROUP BY elections.id
            ORDER BY elections.created_at DESC
            """
        ).fetchall()
        alerts = db.execute("SELECT * FROM ai_alerts ORDER BY severity DESC, created_at DESC LIMIT 10").fetchall()
    return {"elections": [dict(row) for row in elections], "alerts": [dict(row) for row in alerts]}


@router.get("/audit-logs")
def audit_logs(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        rows = db.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100").fetchall()
    return {"audit_logs": [dict(row) for row in rows]}


@router.get("/security-alerts")
def security_alerts(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        rows = db.execute("SELECT * FROM ai_alerts ORDER BY severity DESC, created_at DESC").fetchall()
    return {"alerts": [dict(row) for row in rows]}


@router.put("/security-alerts/{alert_id}/resolve", response_model=MessageResponse)
async def resolve_security_alert(
    alert_id: int,
    payload: AlertResolveRequest,
    admin: UserPublic = Depends(require_admin),
) -> dict:
    with get_connection() as db:
        cursor = db.execute(
            """
            UPDATE ai_alerts
            SET status = ?, resolved_at = CASE WHEN ? = 'RESOLVED' THEN CURRENT_TIMESTAMP ELSE resolved_at END
            WHERE id = ?
            """,
            (payload.status, payload.status, alert_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found.")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'SECURITY', 'AI_ALERT_UPDATED', ?)",
            (admin.id, admin.email, f"Alert {alert_id} set to {payload.status}."),
        )
    await manager.broadcast("security:alerts", {"type": "ALERT_UPDATED", "alert_id": alert_id, "status": payload.status})
    return {"message": "Security alert updated."}


@router.get("/notifications")
def notifications(admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM notifications
            WHERE user_id = ? OR role_target IN (?, 'ADMIN')
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (admin.id, admin.role),
        ).fetchall()
    return {"notifications": [dict(row) for row in rows]}




@router.post("/notifications")
async def create_notification(payload: NotificationCreate, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        cursor = db.execute(
            """
            INSERT INTO notifications (user_id, role_target, title, message, type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.user_id, payload.role_target, payload.title, payload.message, payload.type),
        )
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'NOTIFICATION_CREATED', ?)",
            (admin.id, admin.email, payload.title),
        )
    notification = {"id": cursor.lastrowid, **payload.model_dump()}
    await manager.broadcast("admin:notifications", {"type": "NOTIFICATION_CREATED", "notification": notification})
    return {"message": "Notification created.", "notification_id": cursor.lastrowid}


@router.put("/notifications/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(notification_id: int, _: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    return {"message": "Notification marked as read."}


@router.get("/smtp-status")
def smtp_status(_: UserPublic = Depends(require_admin)) -> dict:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"]
    configured = {key: bool(os.getenv(key) or os.getenv(key.lower())) for key in required}
    ready = all(configured.values())
    return {
        "ready": ready,
        "configured": configured,
        "message": "SMTP is ready for real OTP email." if ready else "SMTP is incomplete; dev OTP fallback will be used.",
    }
