from __future__ import annotations

import json
import secrets
import base64
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request
import qrcode

from ..database import get_connection
from ..dependencies import get_current_user, require_admin
from ..firebase_client import sync_document
from ..schemas import UserPublic, VoteCreate
from ..websocket_manager import manager

router = APIRouter(tags=["Voting"])


def _leaderboard(db, election_id: int) -> list[dict]:
    return [
        dict(row)
        for row in db.execute(
            """
            SELECT candidates.id, candidates.name, candidates.party, COUNT(votes.id) AS votes
            FROM candidates
            LEFT JOIN votes ON votes.candidate_id = candidates.id
            WHERE candidates.election_id = ?
            GROUP BY candidates.id
            ORDER BY votes DESC, candidates.name ASC
            """,
            (election_id,),
        ).fetchall()
    ]


def _qr_base64(payload: str) -> str:
    image = qrcode.make(payload)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}***@{domain}"


def _mask_cnic(cnic: str | None) -> str:
    if not cnic:
        return "Not available"
    digits = "".join(ch for ch in cnic if ch.isdigit())
    if len(digits) < 5:
        return "***"
    return f"{digits[:5]}-*******-{digits[-1]}"


def _receipt_scan_text(receipt: dict) -> str:
    return "\n".join(
        [
            "SMARTVOTE VERIFIED RECEIPT",
            f"Status: Valid ballot counted",
            f"Receipt Code: {receipt.get('receipt_code', 'N/A')}",
            f"Election: {receipt.get('election_title', 'N/A')}",
            f"Election Status: {receipt.get('election_status', 'Recorded')}",
            f"Voted Candidate: {receipt.get('name', 'N/A')}",
            f"Party: {receipt.get('party', 'N/A')}",
            f"Candidate ID: {receipt.get('candidate_id', 'N/A')}",
            f"Voter: {receipt.get('voter_name', 'Verified voter')}",
            f"Email: {receipt.get('voter_email_masked', 'Protected')}",
            f"CNIC: {receipt.get('voter_cnic_masked', 'Protected')}",
            f"Issued At: {receipt.get('created_at', 'Just now')}",
            "Privacy: Full voter identity is protected by SmartVote.",
        ]
    )


@router.post("/votes")
async def cast_vote(
    payload: VoteCreate,
    request: Request,
    user: UserPublic = Depends(get_current_user),
) -> dict:
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email verification required.")
    if user.role != "VOTER":
        raise HTTPException(status_code=403, detail="Admin accounts cannot cast votes.")

    receipt = f"SV-{secrets.token_hex(6).upper()}"
    with get_connection() as db:
        election = db.execute("SELECT * FROM elections WHERE id = ?", (payload.election_id,)).fetchone()
        if not election:
            raise HTTPException(status_code=404, detail="Election not found.")
        if election["status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail="Election is not active.")
        candidate = db.execute(
            "SELECT * FROM candidates WHERE id = ? AND election_id = ?",
            (payload.candidate_id, payload.election_id),
        ).fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found for this election.")
        receipt_payload = _receipt_scan_text(
            {
                "receipt_code": receipt,
                "election_title": election["title"],
                "election_status": election["status"],
                "candidate_id": candidate["id"],
                "name": candidate["name"],
                "party": candidate["party"],
                "voter_name": user.full_name,
                "voter_email_masked": _mask_email(user.email),
                "voter_cnic_masked": _mask_cnic(user.cnic),
            }
        )
        qr_png_base64 = _qr_base64(receipt_payload)
        existing = db.execute(
            "SELECT id FROM votes WHERE user_id = ? AND election_id = ?",
            (user.id, payload.election_id),
        ).fetchone()
        if existing:
            db.execute(
                "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail, severity) VALUES (?, ?, 'VOTE', 'DUPLICATE_VOTE_BLOCKED', ?, 'HIGH')",
                (user.id, user.email, "Duplicate vote attempt blocked."),
            )
            db.execute(
                """
                INSERT INTO ai_alerts (election_id, alert_type, severity, title, message, metadata_json)
                VALUES (?, 'FRAUD', 4, 'Duplicate vote blocked', ?, ?)
                """,
                (
                    payload.election_id,
                    f"{user.email} attempted to vote more than once.",
                    json.dumps({"user_id": user.id, "email": user.email}),
                ),
            )
            raise HTTPException(status_code=409, detail="You have already voted in this election.")
        db.execute(
            """
            INSERT INTO votes (user_id, election_id, candidate_id, receipt_code, receipt_qr_payload, ip_address, device_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                payload.election_id,
                payload.candidate_id,
                receipt,
                receipt_payload,
                request.client.host if request.client else None,
                payload.device_hash,
            ),
        )
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'VOTE', 'VOTE_CAST', ?)",
            (user.id, user.email, f"Vote receipt {receipt} issued."),
        )
        leaderboard = _leaderboard(db, payload.election_id)

    sync_document(
        "vote_ledger",
        receipt,
        {
            "receipt_code": receipt,
            "election_id": payload.election_id,
            "candidate_id": payload.candidate_id,
            "user_id": user.id,
            "qr_payload": receipt_payload,
        },
    )
    await manager.broadcast(f"votes:{payload.election_id}", {"type": "VOTE_CAST", "election_id": payload.election_id})
    await manager.broadcast(f"leaderboard:{payload.election_id}", {"type": "LEADERBOARD", "results": leaderboard})
    await manager.broadcast(
        "admin:notifications",
        {"type": "VOTE_CAST", "election_id": payload.election_id, "receipt_code": receipt},
    )
    return {
        "message": "Vote cast successfully.",
        "receipt_code": receipt,
        "qr_payload": receipt_payload,
        "qr_png_base64": qr_png_base64,
    }


def _vote_receipt_row(db, where_clause: str, params: tuple) -> dict | None:
    row = db.execute(
        f"""
        SELECT
            votes.receipt_code,
            votes.receipt_qr_payload,
            votes.election_id,
            votes.candidate_id,
            votes.created_at,
            elections.title AS election_title,
            elections.status AS election_status,
            candidates.name,
            candidates.party,
            candidates.manifesto,
            candidates.image_url,
            users.full_name AS voter_name,
            users.email AS voter_email,
            users.cnic AS voter_cnic
        FROM votes
        JOIN elections ON elections.id = votes.election_id
        JOIN candidates ON candidates.id = votes.candidate_id
        JOIN users ON users.id = votes.user_id
        {where_clause}
        """,
        params,
    ).fetchone()
    if not row:
        return None
    receipt = dict(row)
    receipt["voter_email_masked"] = _mask_email(receipt.pop("voter_email"))
    receipt["voter_cnic_masked"] = _mask_cnic(receipt.pop("voter_cnic"))
    receipt["receipt_qr_payload"] = _receipt_scan_text(receipt)
    receipt["qr_png_base64"] = _qr_base64(receipt["receipt_qr_payload"])
    return receipt


@router.get("/votes/me/latest")
def my_latest_vote(user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        receipt = _vote_receipt_row(
            db,
            "WHERE votes.user_id = ? ORDER BY votes.created_at DESC LIMIT 1",
            (user.id,),
        )
    return {"vote": receipt}


@router.get("/votes/me/{election_id}")
def my_election_vote(election_id: int, user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        receipt = _vote_receipt_row(
            db,
            "WHERE votes.user_id = ? AND votes.election_id = ?",
            (user.id, election_id),
        )
    return {"vote": receipt}


@router.get("/votes/me")
def my_default_vote(user: UserPublic = Depends(get_current_user)) -> dict:
    return my_election_vote(1, user)


@router.get("/votes/receipt/{receipt_code}")
def verify_receipt(receipt_code: str) -> dict:
    with get_connection() as db:
        row = db.execute(
            """
            SELECT
                votes.receipt_code,
                votes.receipt_qr_payload,
                votes.election_id,
                votes.candidate_id,
                votes.created_at,
                elections.title AS election_title,
                elections.status AS election_status,
                candidates.name,
                candidates.party,
                candidates.manifesto,
                candidates.image_url,
                users.full_name AS voter_name,
                users.email AS voter_email,
                users.cnic AS voter_cnic
            FROM votes
            JOIN elections ON elections.id = votes.election_id
            JOIN candidates ON candidates.id = votes.candidate_id
            JOIN users ON users.id = votes.user_id
            WHERE receipt_code = ?
            """,
            (receipt_code,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    receipt = dict(row)
    receipt["voter_email_masked"] = _mask_email(receipt.pop("voter_email"))
    receipt["voter_cnic_masked"] = _mask_cnic(receipt.pop("voter_cnic"))
    receipt["receipt_qr_payload"] = _receipt_scan_text(receipt)
    receipt["qr_png_base64"] = _qr_base64(receipt["receipt_qr_payload"])
    return {"valid": True, "receipt": receipt}


@router.get("/admin/elections/{election_id}/results")
def admin_results(election_id: int, _: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        results = _leaderboard(db, election_id)
        total = db.execute("SELECT COUNT(*) FROM votes WHERE election_id = ?", (election_id,)).fetchone()[0]
    return {"total_votes": total, "results": results}


@router.get("/elections/{election_id}/leaderboard")
def public_leaderboard(election_id: int) -> dict:
    with get_connection() as db:
        election = db.execute("SELECT status FROM elections WHERE id = ?", (election_id,)).fetchone()
        if not election:
            raise HTTPException(status_code=404, detail="Election not found.")
        results = _leaderboard(db, election_id)
        total = db.execute("SELECT COUNT(*) FROM votes WHERE election_id = ?", (election_id,)).fetchone()[0]
    return {"election_status": election["status"], "total_votes": total, "results": results}
