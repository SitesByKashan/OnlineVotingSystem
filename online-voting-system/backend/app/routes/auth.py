from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import get_settings
from ..database import get_connection
from ..dependencies import get_current_user
from ..emailer import send_otp_email
from ..firebase_client import sync_document
from ..schemas import (
    EmailRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserPublic,
    VerifyOtpRequest,
)
from ..security import create_access_token, decode_access_token, hash_otp, hash_password, oauth2_scheme, utc_now, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


def row_to_user(row) -> UserPublic:
    verified = row["is_email_verified"] if "is_email_verified" in row.keys() else row["is_verified"]
    return UserPublic(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        cnic=row["cnic"] if "cnic" in row.keys() else None,
        role=str(row["role"]).upper(),
        is_verified=bool(verified),
        is_blocked=bool(row["is_blocked"]) if "is_blocked" in row.keys() else False,
    )


def create_otp(db, user_id: int, email: str, full_name: str, purpose: str) -> dict:
    otp = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = (utc_now() + timedelta(minutes=get_settings().otp_expiry_minutes)).isoformat()
    db.execute(
        """
        INSERT INTO otp_codes (user_id, email, code_hash, purpose, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, email, hash_otp(otp), purpose, expires_at),
    )
    sent = send_otp_email(email, full_name, otp, purpose)
    return {"email_sent": sent, "dev_otp": otp if (not sent and get_settings().show_dev_otp) else None}


def verify_otp_code(db, email: str, otp: str, purpose: str):
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="No account found for this email.")
    code = db.execute(
        """
        SELECT * FROM otp_codes
        WHERE user_id = ? AND purpose = ? AND used_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user["id"], purpose),
    ).fetchone()
    if not code:
        raise HTTPException(status_code=400, detail="No active OTP. Please request a new one.")
    if code["attempts"] >= get_settings().otp_max_attempts:
        raise HTTPException(status_code=429, detail="Too many OTP attempts.")
    if code["expires_at"] < utc_now().isoformat():
        raise HTTPException(status_code=400, detail="OTP expired.")
    if hash_otp(otp) != code["code_hash"]:
        db.execute("UPDATE otp_codes SET attempts = attempts + 1 WHERE id = ?", (code["id"],))
        raise HTTPException(status_code=400, detail="Invalid OTP.")
    db.execute("UPDATE otp_codes SET used_at = CURRENT_TIMESTAMP WHERE id = ?", (code["id"],))
    return user


@router.post("/signup")
def signup(payload: SignupRequest) -> dict:
    email = payload.email.lower()
    cnic = payload.cnic.replace("-", "").strip()
    with get_connection() as db:
        existing = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        cnic_owner = db.execute("SELECT * FROM users WHERE cnic = ? AND email != ?", (cnic, email)).fetchone()
        if cnic_owner:
            raise HTTPException(status_code=409, detail="This CNIC is already active with another email.")
        if existing and bool(existing["is_email_verified"] if "is_email_verified" in existing.keys() else existing["is_verified"]):
            raise HTTPException(status_code=409, detail="Email already registered.")
        if existing:
            user_id = existing["id"]
            full_name = existing["full_name"]
            db.execute(
                "UPDATE users SET password_hash = ?, cnic = ? WHERE id = ?",
                (hash_password(payload.password), cnic, user_id),
            )
        else:
            role = "SUPER_ADMIN" if email == "admin@gmail.com" else "VOTER"
            cursor = db.execute(
                """
                INSERT INTO users (full_name, email, cnic, password_hash, role, is_email_verified)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (payload.full_name.strip(), email, cnic, hash_password(payload.password), role),
            )
            user_id = cursor.lastrowid
            full_name = payload.full_name.strip()
        otp_status = create_otp(db, user_id, email, full_name, "EMAIL_VERIFICATION")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'AUTH', 'SIGNUP_OTP_SENT', ?)",
            (user_id, email, "Email verification OTP generated."),
        )
    sync_document(
        "users",
        user_id,
        {"id": user_id, "full_name": full_name, "email": email, "cnic": cnic, "role": "VOTER", "is_verified": False},
    )
    return {"message": "Signup started. Verify your email with OTP.", "email": email, **otp_status}


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyOtpRequest) -> dict:
    with get_connection() as db:
        user = verify_otp_code(db, payload.email.lower(), payload.otp, "EMAIL_VERIFICATION")
        db.execute("UPDATE users SET is_email_verified = 1 WHERE id = ?", (user["id"],))
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'AUTH', 'EMAIL_VERIFIED', ?)",
            (user["id"], payload.email.lower(), "User email verified successfully."),
        )
    sync_document("users", user["id"], {"is_verified": True})
    return {"message": "Email verified. You can now sign in."}


@router.post("/resend-otp")
def resend_otp(payload: EmailRequest) -> dict:
    email = payload.email.lower()
    with get_connection() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="No account found for this email.")
        otp_status = create_otp(db, user["id"], email, user["full_name"], "EMAIL_VERIFICATION")
    return {"message": "A fresh OTP has been sent.", "email": email, **otp_status}


@router.post("/forgot-password")
def forgot_password(payload: EmailRequest) -> dict:
    email = payload.email.lower()
    with get_connection() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="No account found for this email.")
        otp_status = create_otp(db, user["id"], email, user["full_name"], "FORGOT_PASSWORD")
    return {"message": "Password reset OTP sent.", "email": email, **otp_status}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest) -> dict:
    email = payload.email.lower()
    with get_connection() as db:
        user = verify_otp_code(db, email, payload.otp, "FORGOT_PASSWORD")
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(payload.new_password), user["id"]))
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'AUTH', 'PASSWORD_RESET', ?)",
            (user["id"], email, "Password reset completed."),
        )
    return {"message": "Password reset successful."}


@router.post("/login", response_model=TokenResponse)
@router.post("/signin", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    email = payload.email.lower()
    with get_connection() as db:
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"]):
            db.execute(
                "INSERT INTO audit_logs (actor_email, module, action, detail, severity, ip_address) VALUES (?, 'AUTH', 'LOGIN_FAILED', ?, 'MEDIUM', ?)",
                (email, "Invalid login attempt.", request.client.host if request.client else None),
            )
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        user = row_to_user(row)
        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Please verify your email first.")
        if user.is_blocked:
            raise HTTPException(status_code=403, detail="Your account is blocked.")
        token, jti, expires_at = create_access_token(user.id, user.role)
        db.execute(
            """
            INSERT INTO jwt_sessions (user_id, token_jti, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user.id,
                jti,
                request.client.host if request.client else None,
                request.headers.get("user-agent"),
                expires_at.isoformat(),
            ),
        )
    return TokenResponse(access_token=token, user=user)


@router.get("/me")
def me(user: UserPublic = Depends(get_current_user)) -> dict:
    return {"user": user}


@router.post("/logout", response_model=MessageResponse)
def logout(token: str = Depends(oauth2_scheme), user: UserPublic = Depends(get_current_user)) -> dict:
    payload = decode_access_token(token)
    with get_connection() as db:
        db.execute(
            "UPDATE jwt_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE token_jti = ? AND user_id = ?",
            (payload.get("jti"), user.id),
        )
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'AUTH', 'LOGOUT', ?)",
            (user.id, user.email, "JWT session revoked."),
        )
    return {"message": "Logged out successfully."}


@router.get("/sessions")
def sessions(user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT id, ip_address, user_agent, expires_at, revoked_at, created_at
            FROM jwt_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (user.id,),
        ).fetchall()
    return {"sessions": [dict(row) for row in rows]}
