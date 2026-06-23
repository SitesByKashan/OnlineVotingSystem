from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from .database import get_connection
from .schemas import UserPublic
from .security import decode_access_token, oauth2_scheme


def _row_to_user(row) -> UserPublic:
    is_verified = row["is_email_verified"] if "is_email_verified" in row.keys() else row["is_verified"]
    return UserPublic(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        cnic=row["cnic"] if "cnic" in row.keys() else None,
        role=str(row["role"]).upper(),
        is_verified=bool(is_verified),
        is_blocked=bool(row["is_blocked"]) if "is_blocked" in row.keys() else False,
    )


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserPublic:
    payload = decode_access_token(token)
    jti = payload.get("jti")
    with get_connection() as db:
        if jti:
            session = db.execute(
                "SELECT revoked_at FROM jwt_sessions WHERE token_jti = ?",
                (jti,),
            ).fetchone()
            if session and session["revoked_at"]:
                raise HTTPException(status_code=401, detail="Token has been revoked.")
        row = db.execute("SELECT * FROM users WHERE id = ?", (payload["sub"],)).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    user = _row_to_user(row)
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked.")
    return user


def require_admin(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
    if user.email.lower() != "admin@gmail.com":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def require_super_admin(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
    if user.email.lower() != "admin@gmail.com":
        raise HTTPException(status_code=403, detail="Super admin access required.")
    return user
