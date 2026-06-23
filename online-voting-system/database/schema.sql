PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'VOTER' CHECK (role IN ('VOTER', 'ADMIN', 'SUPER_ADMIN')),
    is_email_verified INTEGER NOT NULL DEFAULT 0 CHECK (is_email_verified IN (0, 1)),
    is_blocked INTEGER NOT NULL DEFAULT 0 CHECK (is_blocked IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS otp_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('EMAIL_VERIFICATION', 'FORGOT_PASSWORD', 'LOGIN_SECURITY')),
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
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'PAUSED', 'CLOSED', 'PUBLISHED')),
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
    election_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    party TEXT NOT NULL,
    manifesto TEXT NOT NULL,
    image_url TEXT,
    color TEXT NOT NULL DEFAULT 'cyan',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    election_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    receipt_code TEXT NOT NULL UNIQUE,
    receipt_qr_payload TEXT NOT NULL,
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
    module TEXT NOT NULL CHECK (module IN ('AUTH', 'VOTE', 'ADMIN', 'AI', 'SECURITY', 'SYSTEM')),
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'LOW' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
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
    role TEXT NOT NULL CHECK (role IN ('USER', 'ASSISTANT', 'SYSTEM', 'AGENT')),
    content TEXT NOT NULL,
    metadata_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('FRAUD', 'SECURITY', 'TURNOUT', 'SYSTEM')),
    severity INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    metadata_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role_target TEXT CHECK (role_target IN ('VOTER', 'ADMIN', 'SUPER_ADMIN')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'INFO' CHECK (type IN ('INFO', 'SUCCESS', 'WARNING', 'ERROR', 'SECURITY')),
    is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dsa_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL CHECK (module IN ('QUEUE', 'STACK', 'HASH_TABLE', 'BINARY_SEARCH', 'GRAPH', 'PRIORITY_QUEUE')),
    operation TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    explanation TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_verified ON users(is_email_verified);
CREATE INDEX IF NOT EXISTS idx_otps_user_purpose ON otp_codes(user_id, purpose);
CREATE INDEX IF NOT EXISTS idx_otps_email_purpose ON otp_codes(email, purpose);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON jwt_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_jti ON jwt_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_elections_status ON elections(status);
CREATE INDEX IF NOT EXISTS idx_candidates_election ON candidates(election_id);
CREATE INDEX IF NOT EXISTS idx_votes_election ON votes(election_id);
CREATE INDEX IF NOT EXISTS idx_votes_candidate ON votes(candidate_id);
CREATE INDEX IF NOT EXISTS idx_votes_user_election ON votes(user_id, election_id);
CREATE INDEX IF NOT EXISTS idx_audit_module_action ON audit_logs(module, action);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_security_risk ON security_events(risk_score);
CREATE INDEX IF NOT EXISTS idx_security_user ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_alerts_status_severity ON ai_alerts(status, severity);
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read);
