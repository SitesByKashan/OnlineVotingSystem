PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO users (id, full_name, email, password_hash, role, is_email_verified, is_blocked)
VALUES
    (1, 'Election Super Admin', 'admin@gmail.com', 'smartvote_admin_seed_salt_2026$kJETY7Ot8s2Zvt7//SWXX406J4s/ZK7tbSJu/C/cwbk=', 'SUPER_ADMIN', 1, 0),
    (2, 'Ayesha Demo Voter', 'ayesha.voter@example.com', 'smartvote_voter_seed_salt_2026$Xy3YBZJtqhSOTUT1DfhDL6SakUcyvYjH5su4XhEOfmU=', 'VOTER', 1, 0),
    (3, 'Bilal Demo Voter', 'bilal.voter@example.com', 'smartvote_voter_seed_salt_2026$Xy3YBZJtqhSOTUT1DfhDL6SakUcyvYjH5su4XhEOfmU=', 'VOTER', 1, 0),
    (4, 'Security Admin', 'security.admin@example.com', 'smartvote_admin_seed_salt_2026$kJETY7Ot8s2Zvt7//SWXX406J4s/ZK7tbSJu/C/cwbk=', 'ADMIN', 1, 0);

INSERT OR IGNORE INTO elections (id, title, description, status, start_time, end_time, created_by)
VALUES
    (1, 'SSUET Student Council Election 2026', 'Main student council election for exhibition demo.', 'ACTIVE', '2026-06-13 09:00:00', '2026-06-13 17:00:00', 1),
    (2, 'Computer Science Society Poll', 'Demo departmental poll for DSA and AI showcase.', 'DRAFT', NULL, NULL, 1);

INSERT OR IGNORE INTO candidates (id, election_id, name, party, manifesto, image_url, color)
VALUES
    (1, 1, 'Ayesha Khan', 'Future Alliance', 'Digital campuses, transparent student funds, and AI-supported student services.', NULL, 'cyan'),
    (2, 1, 'Bilal Ahmed', 'Civic Reform', 'Fair representation, secure records, and faster complaint resolution.', NULL, 'green'),
    (3, 1, 'Zara Malik', 'Unity Front', 'Inclusive events, scholarship discovery, and student wellbeing support.', NULL, 'amber'),
    (4, 2, 'Hamza Tariq', 'Tech Vision', 'More hackathons, better labs, and project mentorship.', NULL, 'cyan');

INSERT OR IGNORE INTO votes (id, user_id, election_id, candidate_id, receipt_code, receipt_qr_payload, receipt_qr_path, ip_address, device_hash)
VALUES
    (1, 2, 1, 1, 'SV-DEMO-A1B2C3', '{"receipt":"SV-DEMO-A1B2C3","electionId":1,"verified":true}', '/receipts/SV-DEMO-A1B2C3.png', '127.0.0.1', 'demo-device-ayesha');

INSERT OR IGNORE INTO audit_logs (id, actor_id, actor_email, module, action, detail, severity, ip_address, metadata_json)
VALUES
    (1, 1, 'admin@gmail.com', 'ADMIN', 'ELECTION_CREATED', 'Seed election created for demo.', 'LOW', '127.0.0.1', '{"electionId":1}'),
    (2, 2, 'ayesha.voter@example.com', 'VOTE', 'VOTE_CAST', 'Demo vote receipt SV-DEMO-A1B2C3 issued.', 'LOW', '127.0.0.1', '{"receipt":"SV-DEMO-A1B2C3"}'),
    (3, NULL, 'system@smartvote.local', 'AI', 'FRAUD_SCAN_COMPLETED', 'AI fraud scan completed with low risk.', 'LOW', NULL, '{"risk":"LOW"}');

INSERT OR IGNORE INTO security_events (id, user_id, event_type, risk_score, ip_address, device_hash, description, metadata_json)
VALUES
    (1, 2, 'NORMAL_VOTE', 5, '127.0.0.1', 'demo-device-ayesha', 'Verified voter cast one valid vote.', '{"electionId":1}'),
    (2, 3, 'FAILED_LOGIN', 35, '127.0.0.1', 'demo-device-bilal', 'Failed login attempt captured for monitoring.', '{"attempts":1}');

INSERT OR IGNORE INTO ai_conversations (id, user_id, context, title)
VALUES
    (1, 2, 'VOTER_CHATBOT', 'How to vote'),
    (2, 1, 'ADMIN_COPILOT', 'Election health summary');

INSERT OR IGNORE INTO ai_messages (id, conversation_id, role, content, metadata_json)
VALUES
    (1, 1, 'USER', 'How do I cast my vote?', NULL),
    (2, 1, 'ASSISTANT', 'Verify your email, sign in, open the active election, and cast one encrypted vote.', '{"intent":"vote_help"}'),
    (3, 2, 'AGENT', 'Turnout is stable and no high-risk fraud pattern is detected.', '{"risk":"LOW"}');

INSERT OR IGNORE INTO ai_alerts (id, election_id, alert_type, severity, title, message, status, metadata_json)
VALUES
    (1, 1, 'SECURITY', 1, 'System Healthy', 'No critical security alerts detected.', 'OPEN', '{"source":"seed"}'),
    (2, 1, 'TURNOUT', 2, 'Turnout Watch', 'Monitor vote count during live demo.', 'OPEN', '{"threshold":80}');

INSERT OR IGNORE INTO notifications (id, user_id, role_target, title, message, type, is_read)
VALUES
    (1, 1, 'SUPER_ADMIN', 'Election Started', 'SSUET Student Council Election is active.', 'SUCCESS', 0),
    (2, NULL, 'ADMIN', 'AI Agent Ready', 'AI fraud detection and live monitoring are enabled.', 'INFO', 0);

INSERT OR IGNORE INTO dsa_operations (id, module, operation, input_json, output_json, explanation)
VALUES
    (1, 'QUEUE', 'ENQUEUE_OTP_EMAIL', '{"email":"ayesha.voter@example.com"}', '{"position":1}', 'OTP email jobs are processed in FIFO order.'),
    (2, 'STACK', 'PUSH_ADMIN_ACTION', '{"action":"ELECTION_CREATED"}', '{"stackSize":1}', 'Admin actions can be tracked using stack behavior.'),
    (3, 'HASH_TABLE', 'LOOKUP_VOTER_STATUS', '{"email":"ayesha.voter@example.com"}', '{"hasVoted":true}', 'Hash table lookup gives fast voter status checks.'),
    (4, 'BINARY_SEARCH', 'SEARCH_AUDIT_BY_TIME', '{"timestamp":"2026-06-13 09:00:00"}', '{"found":true}', 'Sorted audit logs can be searched using binary search.'),
    (5, 'GRAPH', 'ADD_DEVICE_EDGE', '{"user":"ayesha","device":"demo-device-ayesha"}', '{"edges":1}', 'User-device-IP relationships can be modeled as a graph.'),
    (6, 'PRIORITY_QUEUE', 'PUSH_AI_ALERT', '{"severity":2}', '{"topSeverity":2}', 'AI alerts are prioritized by risk severity.');
