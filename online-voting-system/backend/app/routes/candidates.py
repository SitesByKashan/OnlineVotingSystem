from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_connection
from ..dependencies import get_current_user, require_admin
from ..firebase_client import sync_document
from ..schemas import CandidateApplicationCreate, CandidateApplicationReview, CandidateCreate, CandidateUpdate, MessageResponse, UserPublic
from ..websocket_manager import manager

router = APIRouter(tags=["Candidates"])


@router.get("/elections/{election_id}/candidates")
def list_candidates(election_id: int) -> dict:
    with get_connection() as db:
        rows = db.execute("SELECT * FROM candidates WHERE election_id = ? ORDER BY id", (election_id,)).fetchall()
    return {"candidates": [dict(row) for row in rows]}


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: int) -> dict:
    with get_connection() as db:
        row = db.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {"candidate": dict(row)}


@router.get("/elections/candidates")
def list_default_candidates() -> dict:
    return list_candidates(1)


@router.post("/candidate-applications")
async def apply_candidate(payload: CandidateApplicationCreate, user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        existing = db.execute(
            """
            SELECT id FROM candidate_applications
            WHERE user_id = ? AND election_id = ?
            """,
            (user.id, payload.election_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="You have already applied as a candidate for this election.")
        cursor = db.execute(
            """
            INSERT INTO candidate_applications (user_id, election_id, full_name, party, manifesto, image_url, experience)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user.id, payload.election_id, payload.full_name, payload.party, payload.manifesto, payload.image_url, payload.experience),
        )
        db.execute(
            """
            INSERT INTO notifications (role_target, title, message, type)
            VALUES ('SUPER_ADMIN', 'New candidate application', ?, 'INFO')
            """,
            (f"{payload.full_name} applied for election #{payload.election_id}.",),
        )
    sync_document(
        "candidate_applications",
        cursor.lastrowid,
        {
            "id": cursor.lastrowid,
            "user_id": user.id,
            "election_id": payload.election_id,
            "full_name": payload.full_name,
            "party": payload.party,
            "image_url": payload.image_url,
            "status": "PENDING",
        },
    )
    await manager.broadcast("admin:notifications", {"type": "CANDIDATE_APPLICATION", "application_id": cursor.lastrowid})
    return {"message": "Candidate application submitted.", "application_id": cursor.lastrowid}


@router.get("/candidate-applications/me")
def my_candidate_applications(user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        rows = db.execute(
            "SELECT * FROM candidate_applications WHERE user_id = ? ORDER BY created_at DESC",
            (user.id,),
        ).fetchall()
    return {"applications": [dict(row) for row in rows]}


@router.post("/admin/candidates")
def create_candidate(payload: CandidateCreate, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        election = db.execute("SELECT id FROM elections WHERE id = ?", (payload.election_id,)).fetchone()
        if not election:
            raise HTTPException(status_code=404, detail="Election not found.")
        cursor = db.execute(
            """
            INSERT INTO candidates (election_id, name, party, manifesto, image_url, color)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.election_id, payload.name, payload.party, payload.manifesto, payload.image_url, payload.color),
        )
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'CANDIDATE_CREATED', ?)",
            (admin.id, admin.email, f"{payload.name} added."),
        )
    return {"message": "Candidate created.", "candidate_id": cursor.lastrowid}


@router.get("/admin/candidate-applications")
def admin_candidate_applications(_: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT candidate_applications.*, users.email
            FROM candidate_applications
            JOIN users ON users.id = candidate_applications.user_id
            ORDER BY candidate_applications.created_at DESC
            """
        ).fetchall()
    return {"applications": [dict(row) for row in rows]}


@router.put("/admin/candidate-applications/{application_id}/review")
async def review_candidate_application(
    application_id: int,
    payload: CandidateApplicationReview,
    admin: UserPublic = Depends(require_admin),
) -> dict:
    with get_connection() as db:
        application = db.execute("SELECT * FROM candidate_applications WHERE id = ?", (application_id,)).fetchone()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found.")
        if application["status"] != "PENDING":
            raise HTTPException(status_code=409, detail="Application already reviewed.")

        candidate_id = None
        if payload.status == "ACCEPTED":
            cursor = db.execute(
                """
                INSERT INTO candidates (election_id, name, party, manifesto, image_url, color)
                VALUES (?, ?, ?, ?, ?, 'cyan')
                """,
                (application["election_id"], application["full_name"], application["party"], application["manifesto"], application["image_url"]),
            )
            candidate_id = cursor.lastrowid

        db.execute(
            """
            UPDATE candidate_applications
            SET status = ?, candidate_id = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (payload.status, candidate_id, admin.id, application_id),
        )
        db.execute(
            """
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
            """,
            (
                application["user_id"],
                f"Candidate application {payload.status.lower()}",
                "Your application was accepted and you are now listed as a candidate." if payload.status == "ACCEPTED" else "Your candidate application was declined.",
                "SUCCESS" if payload.status == "ACCEPTED" else "WARNING",
            ),
        )
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'CANDIDATE_APPLICATION_REVIEWED', ?)",
            (admin.id, admin.email, f"Application {application_id} {payload.status}."),
        )
    sync_document(
        "candidate_applications",
        application_id,
        {"status": payload.status, "reviewed_by": admin.id, "candidate_id": candidate_id},
    )
    await manager.broadcast("admin:notifications", {"type": "CANDIDATE_APPLICATION_REVIEWED", "application_id": application_id})
    return {"message": f"Application {payload.status.lower()}.", "candidate_id": candidate_id}


@router.get("/candidate-results/me")
def my_candidate_results(user: UserPublic = Depends(get_current_user)) -> dict:
    with get_connection() as db:
        applications = db.execute(
            """
            SELECT candidate_applications.*, elections.title AS election_title, elections.status AS election_status
            FROM candidate_applications
            JOIN elections ON elections.id = candidate_applications.election_id
            WHERE candidate_applications.user_id = ? AND candidate_applications.status = 'ACCEPTED'
            ORDER BY candidate_applications.created_at DESC
            """,
            (user.id,),
        ).fetchall()
        campaigns = []
        for application in applications:
            candidate_id = application["candidate_id"]
            if not candidate_id:
                candidate = db.execute(
                    """
                    SELECT id FROM candidates
                    WHERE election_id = ? AND name = ? AND party = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (application["election_id"], application["full_name"], application["party"]),
                ).fetchone()
                candidate_id = candidate["id"] if candidate else None
            if not candidate_id:
                continue

            vote_count = db.execute("SELECT COUNT(*) FROM votes WHERE candidate_id = ?", (candidate_id,)).fetchone()[0]
            election_total = db.execute("SELECT COUNT(*) FROM votes WHERE election_id = ?", (application["election_id"],)).fetchone()[0]
            receipts = db.execute(
                """
                SELECT receipt_code, created_at
                FROM votes
                WHERE candidate_id = ?
                ORDER BY created_at DESC
                """,
                (candidate_id,),
            ).fetchall()
            campaigns.append(
                {
                    "candidate_id": candidate_id,
                    "election_id": application["election_id"],
                    "election_title": application["election_title"],
                    "election_status": application["election_status"],
                    "name": application["full_name"],
                    "party": application["party"],
                    "image_url": application["image_url"],
                    "votes": vote_count,
                    "election_total_votes": election_total,
                    "vote_share": round((vote_count / election_total) * 100, 2) if election_total else 0,
                    "anonymous_votes": [
                        {"receipt": f"{row['receipt_code'][:6]}...{row['receipt_code'][-4:]}", "created_at": row["created_at"]}
                        for row in receipts
                    ],
                }
            )
    return {"campaigns": campaigns}


@router.put("/admin/candidates/{candidate_id}", response_model=MessageResponse)
def update_candidate(candidate_id: int, payload: CandidateUpdate, admin: UserPublic = Depends(require_admin)) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No changes supplied."}
    fields = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [candidate_id]
    with get_connection() as db:
        cursor = db.execute(f"UPDATE candidates SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found.")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'CANDIDATE_UPDATED', ?)",
            (admin.id, admin.email, f"Candidate {candidate_id} updated."),
        )
    return {"message": "Candidate updated."}


@router.delete("/admin/candidates/{candidate_id}", response_model=MessageResponse)
def delete_candidate(candidate_id: int, admin: UserPublic = Depends(require_admin)) -> dict:
    with get_connection() as db:
        vote_count = db.execute("SELECT COUNT(*) FROM votes WHERE candidate_id = ?", (candidate_id,)).fetchone()[0]
        if vote_count:
            raise HTTPException(status_code=409, detail="Cannot delete candidate with votes.")
        cursor = db.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found.")
        db.execute(
            "INSERT INTO audit_logs (actor_id, actor_email, module, action, detail) VALUES (?, ?, 'ADMIN', 'CANDIDATE_DELETED', ?)",
            (admin.id, admin.email, f"Candidate {candidate_id} deleted."),
        )
    return {"message": "Candidate deleted."}
