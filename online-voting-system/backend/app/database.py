from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from .config import get_settings
from .security import hash_password


def get_connection() -> sqlite3.Connection:
    db_path = Path(get_settings().database_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def db_session() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.OperationalError:
        return set()


def _add_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in _columns(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _fix_votes_unique_constraint(db: sqlite3.Connection) -> None:
    row = db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'votes'").fetchone()
    if not row or "user_id INTEGER NOT NULL UNIQUE" not in row["sql"]:
        return

    db.execute("PRAGMA foreign_keys = OFF")
    try:
        db.executescript(
            """
            CREATE TABLE votes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                election_id INTEGER NOT NULL DEFAULT 1,
                candidate_id INTEGER NOT NULL,
                receipt_code TEXT NOT NULL UNIQUE,
                receipt_qr_payload TEXT NOT NULL DEFAULT '{}',
                receipt_qr_path TEXT,
                ip_address TEXT,
                device_hash TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
                UNIQUE (user_id, election_id)
            );

            INSERT INTO votes_new (
                id, user_id, election_id, candidate_id, receipt_code,
                receipt_qr_payload, receipt_qr_path, ip_address, device_hash, created_at
            )
            SELECT
                id, user_id, election_id, candidate_id, receipt_code,
                receipt_qr_payload, receipt_qr_path, ip_address, device_hash, created_at
            FROM votes;

            DROP TABLE votes;
            ALTER TABLE votes_new RENAME TO votes;
            """
        )
    finally:
        db.execute("PRAGMA foreign_keys = ON")


def init_db() -> None:
    with get_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                cnic TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'VOTER',
                is_email_verified INTEGER NOT NULL DEFAULT 0,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS otp_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                purpose TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                used_at DATETIME,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS jwt_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_jti TEXT NOT NULL UNIQUE,
                refresh_token_hash TEXT,
                ip_address TEXT,
                user_agent TEXT,
                expires_at DATETIME NOT NULL,
                revoked_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                start_time DATETIME,
                end_time DATETIME,
                result_published_at DATETIME,
                created_by INTEGER NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                election_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                party TEXT NOT NULL,
                manifesto TEXT NOT NULL,
                image_url TEXT,
                color TEXT NOT NULL DEFAULT 'cyan',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS candidate_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                election_id INTEGER NOT NULL DEFAULT 1,
                full_name TEXT NOT NULL,
                party TEXT NOT NULL,
                manifesto TEXT NOT NULL,
                image_url TEXT,
                experience TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                candidate_id INTEGER,
                reviewed_by INTEGER,
                reviewed_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
                FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                election_id INTEGER NOT NULL DEFAULT 1,
                candidate_id INTEGER NOT NULL,
                receipt_code TEXT NOT NULL UNIQUE,
                receipt_qr_payload TEXT NOT NULL DEFAULT '{}',
                receipt_qr_path TEXT,
                ip_address TEXT,
                device_hash TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
                UNIQUE (user_id, election_id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                actor_email TEXT NOT NULL,
                module TEXT NOT NULL DEFAULT 'SYSTEM',
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'LOW',
                ip_address TEXT,
                metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                risk_score INTEGER NOT NULL DEFAULT 0,
                ip_address TEXT,
                device_hash TEXT,
                description TEXT NOT NULL,
                metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS ai_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                election_id INTEGER,
                alert_type TEXT NOT NULL,
                severity INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role_target TEXT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'INFO',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                context TEXT NOT NULL DEFAULT 'VOTER_CHATBOT',
                title TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS ai_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dsa_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                operation TEXT NOT NULL,
                input_json TEXT,
                output_json TEXT,
                explanation TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        for table, additions in {
            "users": {
                "cnic": "TEXT",
                "is_email_verified": "INTEGER NOT NULL DEFAULT 0",
                "is_blocked": "INTEGER NOT NULL DEFAULT 0",
                "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
            },
            "otp_codes": {
                "email": "TEXT NOT NULL DEFAULT ''",
                "purpose": "TEXT NOT NULL DEFAULT 'EMAIL_VERIFICATION'",
                "attempts": "INTEGER NOT NULL DEFAULT 0",
            },
            "jwt_sessions": {
                "refresh_token_hash": "TEXT",
            },
            "candidates": {
                "election_id": "INTEGER NOT NULL DEFAULT 1",
                "image_url": "TEXT",
                "color": "TEXT NOT NULL DEFAULT 'cyan'",
                "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
                "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
            },
            "candidate_applications": {
                "image_url": "TEXT",
                "candidate_id": "INTEGER",
            },
            "votes": {
                "election_id": "INTEGER NOT NULL DEFAULT 1",
                "receipt_qr_payload": "TEXT NOT NULL DEFAULT '{}'",
                "receipt_qr_path": "TEXT",
                "ip_address": "TEXT",
                "device_hash": "TEXT",
            },
            "audit_logs": {
                "actor_id": "INTEGER",
                "module": "TEXT NOT NULL DEFAULT 'SYSTEM'",
                "severity": "TEXT NOT NULL DEFAULT 'LOW'",
                "ip_address": "TEXT",
                "metadata_json": "TEXT",
            },
        }.items():
            for column, definition in additions.items():
                _add_column(db, table, column, definition)

        if "is_verified" in _columns(db, "users"):
            db.execute("UPDATE users SET is_email_verified = is_verified WHERE is_email_verified = 0")

        _fix_votes_unique_constraint(db)

        admin_hash = hash_password("admin")
        db.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, is_email_verified, is_blocked)
            VALUES (?, ?, ?, ?, 1, 0)
            ON CONFLICT(email) DO UPDATE SET
                full_name = excluded.full_name,
                password_hash = excluded.password_hash,
                role = excluded.role,
                is_email_verified = 1,
                is_blocked = 0
            """,
            ("Election Super Admin", "admin@gmail.com", admin_hash, "SUPER_ADMIN"),
        )

        admin_id = db.execute("SELECT id FROM users WHERE email = ?", ("admin@gmail.com",)).fetchone()["id"]
        db.execute(
            """
            INSERT OR IGNORE INTO elections (id, title, description, status, start_time, end_time, created_by)
            VALUES (1, ?, ?, 'ACTIVE', DATETIME('now', '-1 hour'), DATETIME('now', '+6 hours'), ?)
            """,
            ("SSUET Student Council Election 2026", "Main exhibition election with live AI monitoring.", admin_id),
        )
        if db.execute("SELECT COUNT(*) FROM candidates WHERE election_id = 1").fetchone()[0] == 0:
            db.executemany(
                """
                INSERT INTO candidates (election_id, name, party, manifesto, color)
                VALUES (1, ?, ?, ?, ?)
                """,
                [
                    ("Ayesha Khan", "Future Alliance", "Digital campuses and AI-supported services.", "cyan"),
                    ("Bilal Ahmed", "Civic Reform", "Fair representation and transparent records.", "green"),
                    ("Zara Malik", "Unity Front", "Inclusive events and student wellbeing.", "amber"),
                ],
            )

        db.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_cnic_unique ON users(cnic) WHERE cnic IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
            CREATE INDEX IF NOT EXISTS idx_candidate_applications_status ON candidate_applications(status);
            CREATE INDEX IF NOT EXISTS idx_otps_user_purpose ON otp_codes(user_id, purpose);
            CREATE INDEX IF NOT EXISTS idx_sessions_jti ON jwt_sessions(token_jti);
            CREATE INDEX IF NOT EXISTS idx_elections_status ON elections(status);
            CREATE INDEX IF NOT EXISTS idx_candidates_election ON candidates(election_id);
            CREATE INDEX IF NOT EXISTS idx_votes_user_election ON votes(user_id, election_id);
            CREATE INDEX IF NOT EXISTS idx_votes_election ON votes(election_id);
            CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_ai_alerts_status_severity ON ai_alerts(status, severity);
            CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read);
            CREATE INDEX IF NOT EXISTS idx_security_risk ON security_events(risk_score);
            """
        )
