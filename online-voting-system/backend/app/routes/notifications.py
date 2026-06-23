from __future__ import annotations

from fastapi import APIRouter, Depends

from ..database import get_connection
from ..dependencies import get_current_user
from ..schemas import UserPublic

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me")
def my_notifications(user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM notifications
            WHERE user_id = ? OR role_target = ?
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (user.id, user.role),
        ).fetchall()
    return {"notifications": [dict(row) for row in rows]}
