from __future__ import annotations

import json

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from ..database import get_connection
from ..dependencies import require_admin
from ..schemas import ChatRequest, UserPublic
from ..security import decode_access_token

router = APIRouter(tags=["AI"])


def _optional_user_id(authorization: str | None) -> int | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
        return int(payload["sub"])
    except Exception:
        return None


def _site_context() -> dict:
    with get_connection() as db:
        users = db.execute("SELECT COUNT(*) FROM users WHERE role = 'VOTER'").fetchone()[0]
        verified = db.execute("SELECT COUNT(*) FROM users WHERE is_email_verified = 1 AND role = 'VOTER'").fetchone()[0]
        votes = db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        elections = db.execute("SELECT COUNT(*) FROM elections").fetchone()[0]
        active = db.execute("SELECT * FROM elections WHERE status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1").fetchone()
        candidates = db.execute(
            """
            SELECT candidates.name, candidates.party, COUNT(votes.id) AS votes
            FROM candidates
            LEFT JOIN votes ON votes.candidate_id = candidates.id
            GROUP BY candidates.id
            ORDER BY votes DESC, candidates.name ASC
            LIMIT 5
            """
        ).fetchall()
        alerts = db.execute("SELECT COUNT(*) FROM ai_alerts WHERE status != 'RESOLVED'").fetchone()[0]
    turnout = round((votes / verified) * 100, 2) if verified else 0
    return {
        "users": users,
        "verified": verified,
        "votes": votes,
        "elections": elections,
        "active": dict(active) if active else None,
        "candidates": [dict(row) for row in candidates],
        "alerts": alerts,
        "turnout": turnout,
    }


@router.post("/ai/chat")
def ai_chat(payload: ChatRequest, authorization: Annotated[str | None, Header()] = None) -> dict:
    user_id = _optional_user_id(authorization)
    text = payload.message.lower()
    context = _site_context()
    active_title = context["active"]["title"] if context["active"] else "No active election"
    top = context["candidates"][0] if context["candidates"] else None
    candidate_lines = ", ".join(f"{row['name']} ({row['votes']} votes)" for row in context["candidates"]) or "No candidates yet"
    if "otp" in text or "email" in text or "verify" in text:
        reply = (
            "OTP flow live SMTP se connected hai. Signup ke baad user email par 6 digit OTP receive karta hai, "
            "phir Verify Email page par OTP enter karke account activate hota hai. Dev OTP screen par show nahi hota."
        )
        actions = ["Open verify email", "Resend OTP", "Check SMTP"]
    elif "result" in text or "leader" in text or "winner" in text:
        reply = (
            f"Live result: active election is '{active_title}'. Total votes: {context['votes']}. "
            f"Turnout: {context['turnout']}%. Current leaderboard: {candidate_lines}."
        )
        actions = ["Open dashboard", "View candidates", "Open receipt verifier"]
    elif "vote" in text or "candidate" in text:
        reply = (
            f"Voting rule: only verified VOTER accounts can cast one vote per election. Active election: '{active_title}'. "
            f"Candidates currently visible: {candidate_lines}. Duplicate votes are blocked by database constraint and AI fraud audit."
        )
        actions = ["Open voter dashboard", "View receipt", "Check election status"]
    elif "admin" in text or "fraud" in text or "security" in text or "ai" in text:
        reply = (
            f"Admin AI modules are connected to real data: {context['verified']} verified voters, "
            f"{context['votes']} votes, {context['alerts']} open AI/security alerts. Fraud scan checks duplicate vote attempts, failed logins, turnout, and audit logs."
        )
        actions = ["Open admin dashboard", "Run fraud scan", "View analytics"]
    else:
        reply = (
            f"SmartVote status: {context['elections']} elections, {context['verified']} verified voters, "
            f"{context['votes']} votes, active election '{active_title}'. Ask me about OTP, candidates, live result, QR receipt, admin, or fraud monitoring."
        )
        actions = ["Live results", "Candidate help", "QR receipt guide"]
    with get_connection() as db:
        cursor = db.execute(
            "INSERT INTO ai_conversations (user_id, context, title) VALUES (?, ?, ?)",
            (user_id, "VOTER_CHATBOT", payload.message[:80]),
        )
        conversation_id = cursor.lastrowid
        db.execute(
            "INSERT INTO ai_messages (conversation_id, role, content, metadata_json) VALUES (?, 'USER', ?, ?)",
            (conversation_id, payload.message, json.dumps({"page": payload.page})),
        )
        db.execute(
            "INSERT INTO ai_messages (conversation_id, role, content, metadata_json) VALUES (?, 'ASSISTANT', ?, ?)",
            (conversation_id, reply, json.dumps({"actions": actions})),
        )
    return {
        "reply": reply,
        "conversation_id": conversation_id,
        "agent": {"mode": "Election Guardian", "page": payload.page, "actions": actions},
    }


@router.post("/admin/ai/copilot")
def admin_copilot(payload: ChatRequest, _: UserPublic = Depends(require_admin)) -> dict:
    return {
        "reply": f"Admin Copilot summary for '{payload.message}': monitor turnout, verify SMTP, export audit logs, and resolve high severity alerts first.",
        "actions": ["Run fraud scan", "Export audit logs", "Review security alerts"],
    }


@router.get("/admin/ai/fraud-scan")
@router.get("/admin/agent-scan")
def fraud_scan(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        verified = db.execute("SELECT COUNT(*) FROM users WHERE is_email_verified = 1").fetchone()[0]
        votes = db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        duplicates = db.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'DUPLICATE_VOTE_BLOCKED'").fetchone()[0]
        failed = db.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'LOGIN_FAILED'").fetchone()[0]
        latest = db.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 5").fetchall()
    turnout = round((votes / verified) * 100, 2) if verified else 0
    risk = "LOW"
    if duplicates > 3 or failed > 10:
        risk = "HIGH"
    elif duplicates or failed > 3:
        risk = "MEDIUM"
    response = {
        "risk_level": risk.title(),
        "summary": f"{votes} votes from {verified} verified voters. Turnout is {turnout}%.",
        "signals": {"verified_users": verified, "votes": votes, "duplicate_attempts": duplicates, "failed_logins": failed},
        "recommendations": ["Keep OTP enabled.", "Review failed logins.", "Export audit logs before publishing results."],
        "latest_logs": [dict(row) for row in latest],
    }
    if risk != "LOW":
        with get_connection() as db:
            db.execute(
                """
                INSERT INTO ai_alerts (alert_type, severity, title, message, metadata_json)
                VALUES ('FRAUD', ?, ?, ?, ?)
                """,
                (
                    4 if risk == "HIGH" else 2,
                    f"{risk.title()} fraud risk detected",
                    response["summary"],
                    json.dumps(response["signals"]),
                ),
            )
    return response


@router.get("/admin/ai/security-scan")
def security_scan(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        events = db.execute("SELECT * FROM security_events ORDER BY risk_score DESC LIMIT 10").fetchall()
    return {"events": [dict(row) for row in events]}


@router.get("/admin/ai/agent-report")
def agent_report(_: UserPublic = Depends(require_admin)) -> dict:
    scan = fraud_scan(_)
    return {
        "title": "SmartVote AI Agent Report",
        "risk_level": scan["risk_level"],
        "summary": scan["summary"],
        "next_actions": scan["recommendations"],
    }
