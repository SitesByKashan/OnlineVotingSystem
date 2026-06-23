"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import BrandLogo from "../components/BrandLogo";
import { apiRequest, clearSession, Election, fileToDataUrl, getStoredUser, getToken } from "../lib/api";

type AdminStats = {
  totals: {
    users: number;
    verified_users: number;
    pending_verification: number;
    votes: number;
    turnout_percent: number;
  };
  results: Array<{ id: number; election_id: number; name: string; party: string; manifesto?: string; image_url?: string | null; votes: number }>;
  audit_logs: Array<{ id: number; actor_email: string; action: string; detail: string; severity?: string; created_at: string }>;
};

type AdminUser = {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_verified: number;
  is_blocked: number;
  created_at: string;
  receipt_code?: string;
};

type SecurityAlert = {
  id: number;
  title: string;
  message: string;
  alert_type: string;
  severity: number;
  status: string;
  created_at: string;
};

type SecurityEvent = {
  id: number;
  event_type: string;
  risk_score: number;
  ip_address?: string;
  description: string;
  created_at: string;
};

type AgentScan = {
  risk_level: string;
  summary: string;
  recommendations: string[];
  signals: Record<string, number>;
};

type SmtpStatus = {
  ready: boolean;
  message: string;
  configured: Record<string, boolean>;
};

type CandidateApplication = {
  id: number;
  full_name: string;
  party: string;
  manifesto: string;
  image_url?: string | null;
  experience: string;
  status: string;
  email: string;
  created_at: string;
};

const tabs = [
  "Command Center",
  "Analytics",
  "Users",
  "Elections",
  "Candidates",
  "Requests",
  "Security",
  "Fraud",
  "AI Agent",
  "Insights",
  "DSA Lab",
  "Graph",
  "Timeline",
  "Ledger",
] as const;

const dsaModules = [
  ["Queue", "OTP jobs and vote processing pipeline", "FIFO"],
  ["Stack", "Admin undo trail and audit rewind", "LIFO"],
  ["Hash Table", "Instant voter and receipt lookup", "O(1)"],
  ["Binary Search", "Sorted audit log investigation", "O(log n)"],
  ["Graph", "User, device, IP, and alert relationships", "Edges"],
  ["Priority Queue", "AI alert ranking by severity", "Heap"],
];

const timelineEvents = [
  ["09:00", "Election opened", "ACTIVE"],
  ["09:12", "First verified ballot", "VOTE"],
  ["09:41", "AI scan completed", "LOW RISK"],
  ["10:18", "SMTP health checked", "READY"],
  ["11:04", "Duplicate attempt blocked", "FRAUD"],
];

const ledgerBlocks = [
  ["#1042", "OTP_VERIFIED", "a91f", "b722"],
  ["#1043", "VOTE_CAST", "b722", "cf31"],
  ["#1044", "AI_SCAN", "cf31", "e8aa"],
  ["#1045", "AUDIT_LOCK", "e8aa", "91bd"],
];

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>("Command Center");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [elections, setElections] = useState<Election[]>([]);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [applications, setApplications] = useState<CandidateApplication[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [agent, setAgent] = useState<AgentScan | null>(null);
  const [smtp, setSmtp] = useState<SmtpStatus | null>(null);
  const [message, setMessage] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null);
  const [accessChecked, setAccessChecked] = useState(false);

  const topCandidate = useMemo(() => stats?.results[0], [stats]);

  function logout() {
    clearSession();
    window.location.href = "/";
  }

  async function loadAdminData() {
    const token = getToken();
    try {
      const [statsData, usersData, electionData, alertsData, smtpData, applicationData] = await Promise.all([
        apiRequest<AdminStats>("/admin/dashboard", { token }),
        apiRequest<{ users: AdminUser[] }>("/admin/users", { token }),
        apiRequest<{ elections: Election[] }>("/elections"),
        apiRequest<{ alerts: SecurityAlert[] }>("/admin/security-alerts", { token }),
        apiRequest<SmtpStatus>("/admin/smtp-status", { token }),
        apiRequest<{ applications: CandidateApplication[] }>("/admin/candidate-applications", { token }),
      ]);
      setStats(statsData);
      setUsers(usersData.users);
      setElections(electionData.elections);
      setAlerts(alertsData.alerts);
      setApplications(applicationData.applications);
      setSmtp(smtpData);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? `${error.message} Admin access required.` : "Unable to load admin dashboard.");
    }
  }

  useEffect(() => {
    const currentUser = getStoredUser();
    setUser(currentUser);
    setAccessChecked(true);
    if (!currentUser || currentUser.email.toLowerCase() !== "admin@gmail.com") {
      window.location.href = currentUser ? "/dashboard" : "/signin";
      return;
    }
    const timer = window.setTimeout(() => {
      loadAdminData();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function runAgentScan() {
    const token = getToken();
    try {
      const [fraudData, securityData] = await Promise.all([
        apiRequest<AgentScan>("/admin/ai/fraud-scan", { token }),
        apiRequest<{ events: SecurityEvent[] }>("/admin/ai/security-scan", { token }),
      ]);
      setAgent(fraudData);
      setSecurityEvents(securityData.events);
      setMessage("AI Agent scan completed.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "AI scan failed.");
    }
  }

  async function createElection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyAction) return;
    const form = new FormData(event.currentTarget);
    try {
      setBusyAction("create-election");
      await apiRequest<{ election_id: number }>("/admin/elections", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({
          title: form.get("title"),
          description: form.get("description"),
        }),
      });
      event.currentTarget.reset();
      await loadAdminData();
      setMessage("Election connected to command center successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create election.");
    } finally {
      setBusyAction("");
    }
  }

  async function updateElectionStatus(electionId: number, status: Election["status"]) {
    if (busyAction) return;
    try {
      setBusyAction(`election-${electionId}-${status}`);
      await apiRequest<{ message: string }>(`/admin/elections/${electionId}/status`, {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ status }),
      });
      await loadAdminData();
      setMessage(`Election moved to ${status}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update election.");
    } finally {
      setBusyAction("");
    }
  }

  async function deleteElection(electionId: number) {
    if (busyAction) return;
    try {
      setBusyAction(`delete-election-${electionId}`);
      await apiRequest<{ message: string }>(`/admin/elections/${electionId}`, {
        method: "DELETE",
        token: getToken(),
      });
      await loadAdminData();
      setMessage("Election deleted from command center.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete election.");
    } finally {
      setBusyAction("");
    }
  }

  async function createCandidate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busyAction) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const imageFile = form.get("image_file");
    const imageUrl = imageFile instanceof File && imageFile.size > 0 ? await fileToDataUrl(imageFile) : null;
    try {
      setBusyAction("create-candidate");
      await apiRequest<{ candidate_id: number }>("/admin/candidates", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({
          election_id: Number(form.get("election_id")),
          name: form.get("name"),
          party: form.get("party"),
          manifesto: form.get("manifesto"),
          image_url: imageUrl,
          color: form.get("color"),
        }),
      });
      formElement.reset();
      await loadAdminData();
      setMessage("Candidate added and synced live.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not add candidate.");
    } finally {
      setBusyAction("");
    }
  }

  async function deleteCandidate(candidateId: number) {
    if (busyAction) return;
    try {
      setBusyAction(`delete-candidate-${candidateId}`);
      await apiRequest<{ message: string }>(`/admin/candidates/${candidateId}`, {
        method: "DELETE",
        token: getToken(),
      });
      await loadAdminData();
      setMessage("Candidate deleted successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete candidate.");
    } finally {
      setBusyAction("");
    }
  }

  async function toggleBlock(target: AdminUser) {
    try {
      await apiRequest<{ message: string }>(`/admin/users/${target.id}/block`, {
        method: "PUT",
        token: getToken(),
        body: JSON.stringify({ is_blocked: !target.is_blocked }),
      });
      await loadAdminData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update user.");
    }
  }

  async function resolveAlert(alertId: number) {
    try {
      await apiRequest<{ message: string }>(`/admin/security-alerts/${alertId}/resolve`, {
        method: "PUT",
        token: getToken(),
        body: JSON.stringify({ status: "RESOLVED" }),
      });
      await loadAdminData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not resolve alert.");
    }
  }

  async function reviewApplication(applicationId: number, status: "ACCEPTED" | "DECLINED") {
    try {
      await apiRequest<{ message: string }>(`/admin/candidate-applications/${applicationId}/review`, {
        method: "PUT",
        token: getToken(),
        body: JSON.stringify({ status }),
      });
      await loadAdminData();
      setMessage(`Candidate application ${status.toLowerCase()}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not review application.");
    }
  }

  if (!accessChecked || user?.email.toLowerCase() !== "admin@gmail.com") {
    return (
      <main className="admin-glass-page">
        <section className="admin-glass-workspace">
          <div className="glass-panel">
            <h1>Admin access required</h1>
            <p>Redirecting to the correct workspace.</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-glass-page">
      <aside className="admin-glass-sidebar">
        <Link className="admin-brand" href="/"><BrandLogo /></Link>
        <nav>
          {tabs.map((tab) => (
            <button className={activeTab === tab ? "active" : ""} type="button" key={tab} onClick={() => setActiveTab(tab)}>
              {tab}
            </button>
          ))}
        </nav>
        <div className="admin-profile-card">
          <span>Signed in</span>
          <strong>{user?.full_name ?? "Admin"}</strong>
          <small>{user?.email ?? "Protected admin account"}</small>
          <Link className="admin-mini-link" href="/dashboard">Open voter dashboard</Link>
          <button className="admin-logout" type="button" onClick={logout}>Logout</button>
        </div>
      </aside>

      <section className="admin-glass-workspace">
        <header className="admin-hero-panel">
          <div>
            <span className="glass-badge">Premium Admin Dashboard</span>
            <h1>Election command center</h1>
            <p>Manage voters, candidates, elections, analytics, security alerts, fraud detection, and the AI agent from one glass console.</p>
            <div className="admin-hero-actions">
              <Link href="/dashboard">Voter dashboard</Link>
              <button type="button" onClick={runAgentScan}>Launch AI scan</button>
            </div>
          </div>
          <div className="admin-orbital-card hero-3d-console">
            <span className="hero-orbit orbit-one" />
            <span className="hero-orbit orbit-two" />
            <span className="hero-orbit orbit-three" />
            <div className="hero-core">
              <span>AI Risk</span>
              <strong>{agent?.risk_level ?? "Standby"}</strong>
              <small>{stats?.totals.votes ?? 0} secured ballots</small>
            </div>
          </div>
        </header>

        {message && <p className="admin-toast">{message}</p>}

        <section className="admin-kpi-grid">
          <div><span>Total users</span><strong>{stats?.totals.users ?? 0}</strong><small>{stats?.totals.verified_users ?? 0} verified</small></div>
          <div><span>Votes cast</span><strong>{stats?.totals.votes ?? 0}</strong><small>{stats?.totals.turnout_percent ?? 0}% turnout</small></div>
          <div><span>Pending OTP</span><strong>{stats?.totals.pending_verification ?? 0}</strong><small>Email verification queue</small></div>
          <div><span>Leading candidate</span><strong>{topCandidate?.name ?? "N/A"}</strong><small>{topCandidate?.votes ?? 0} votes</small></div>
        </section>

        {activeTab === "Command Center" && (
          <section className="command-center-grid">
            <div className="glass-panel command-3d">
              <div className="command-stage">
                <span className="command-ring ring-a" />
                <span className="command-ring ring-b" />
                <span className="command-ring ring-c" />
                <div className="command-core">
                  <strong>{stats?.totals.votes ?? 0}</strong>
                  <span>secured ballots</span>
                </div>
                <div className="command-chip chip-a">JWT</div>
                <div className="command-chip chip-b">OTP</div>
                <div className="command-chip chip-c">AI</div>
              </div>
            </div>
            <div className="glass-panel">
              <h2>Startup product cockpit</h2>
              <p>SmartVote presents a live election operating system: verified identity, fraud defense, vote ledger, analytics, and agentic supervision.</p>
              <div className="insight-stack">
                <span>Live WebSocket analytics ready</span>
                <span>Blockchain-inspired ledger visible</span>
                <span>AI fraud engine connected</span>
                <span>DSA concepts visualized for judges</span>
              </div>
            </div>
          </section>
        )}

        {activeTab === "Analytics" && (
          <section className="admin-section-grid">
            <div className="glass-panel wide">
              <h2>Live analytics</h2>
              {stats?.results.map((row) => (
                <div className="admin-progress-row" key={row.id}>
                  <span>{row.name}</span>
                  <i><b style={{ width: `${Math.max(row.votes * 20, 8)}%` }} /></i>
                  <strong>{row.votes}</strong>
                </div>
              ))}
            </div>
            <div className="glass-panel">
              <h2>SMTP status</h2>
              <strong className={smtp?.ready ? "status-good" : "status-warn"}>{smtp?.ready ? "Ready" : "Incomplete"}</strong>
              <p>{smtp?.message ?? "Checking SMTP configuration..."}</p>
            </div>
          </section>
        )}

        {activeTab === "Users" && (
          <section className="glass-panel">
            <h2>User management</h2>
            <div className="admin-table">
              {users.map((item) => (
                <article key={item.id}>
                  <div><strong>{item.full_name}</strong><span>{item.email}</span></div>
                  <span>{item.role}</span>
                  <span>{item.is_verified ? "Verified" : "Pending"}</span>
                  <span>{item.receipt_code ? "Voted" : "No vote"}</span>
                  <button type="button" onClick={() => toggleBlock(item)}>{item.is_blocked ? "Unblock" : "Block"}</button>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Elections" && (
          <section className="admin-section-grid">
            <form className="glass-panel admin-form" onSubmit={createElection}>
              <h2>Create election</h2>
              <input name="title" placeholder="Election title" required minLength={3} />
              <textarea name="description" placeholder="Election description" required minLength={5} />
              <button type="submit" disabled={busyAction === "create-election"}>
                {busyAction === "create-election" ? "Creating..." : "Create election"}
              </button>
            </form>
            <div className="glass-panel wide">
              <h2>Election management</h2>
              {elections.map((election) => (
                <div className="election-control" key={election.id}>
                  <div><strong>{election.title}</strong><span>{election.description}</span></div>
                  <em>{election.status}</em>
                  <div>
                    {(["ACTIVE", "PAUSED", "CLOSED", "PUBLISHED"] as Election["status"][]).map((status) => (
                      <button
                        type="button"
                        key={status}
                        disabled={Boolean(busyAction)}
                        onClick={() => updateElectionStatus(election.id, status)}
                      >
                        {status}
                      </button>
                    ))}
                    <button
                      className="danger-action"
                      type="button"
                      disabled={Boolean(busyAction)}
                      onClick={() => deleteElection(election.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Candidates" && (
          <section className="admin-section-grid">
            <form className="glass-panel admin-form" onSubmit={createCandidate}>
              <h2>Add candidate</h2>
              <select name="election_id" required>
                {elections.map((election) => <option key={election.id} value={election.id}>{election.title}</option>)}
              </select>
              <input name="name" placeholder="Candidate name" required minLength={3} />
              <input name="party" placeholder="Party name" required minLength={2} />
              <label className="admin-file-upload">
                Candidate picture
                <input name="image_file" type="file" accept="image/*" />
              </label>
              <textarea name="manifesto" placeholder="Manifesto" required minLength={10} />
              <select name="color" defaultValue="cyan">
                <option value="cyan">Cyan</option>
                <option value="green">Green</option>
                <option value="amber">Amber</option>
              </select>
              <button type="submit" disabled={busyAction === "create-candidate"}>
                {busyAction === "create-candidate" ? "Adding..." : "Add candidate"}
              </button>
            </form>
            <div className="glass-panel wide">
              <h2>Candidate performance</h2>
              {stats?.results.map((candidate) => (
                <div className="candidate-admin-row" key={candidate.id}>
                  <div className="candidate-admin-profile">
                    {candidate.image_url ? <img src={candidate.image_url} alt={candidate.name} /> : <span>{candidate.name.slice(0, 2).toUpperCase()}</span>}
                    <div><strong>{candidate.name}</strong><small>Election #{candidate.election_id}</small></div>
                  </div>
                  <span>{candidate.party}</span>
                  <em>{candidate.votes} votes</em>
                  <button
                    className="danger-action"
                    type="button"
                    disabled={Boolean(busyAction)}
                    onClick={() => deleteCandidate(candidate.id)}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Requests" && (
          <section className="glass-panel wide">
            <div className="section-heading compact">
              <span className="glass-badge">Candidate onboarding</span>
              <h2>Candidate application requests</h2>
              <p>Review public applications and promote approved users into the live candidate list.</p>
            </div>
            <div className="admin-table request-table">
              {applications.length === 0 && <p className="notice">No candidate applications yet.</p>}
              {applications.map((application) => (
                <article key={application.id}>
                  <div>
                    <strong>{application.full_name}</strong>
                    <span>{application.email} - {application.party}</span>
                    <small>{application.manifesto}</small>
                  </div>
                  <span>{application.status}</span>
                  <button
                    type="button"
                    disabled={application.status !== "PENDING"}
                    onClick={() => reviewApplication(application.id, "ACCEPTED")}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    disabled={application.status !== "PENDING"}
                    onClick={() => reviewApplication(application.id, "DECLINED")}
                  >
                    Decline
                  </button>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Security" && (
          <section className="admin-section-grid">
            <div className="glass-panel wide">
              <h2>Security center</h2>
              {alerts.map((alert) => (
                <div className="alert-row" key={alert.id}>
                  <div><strong>{alert.title}</strong><span>{alert.message}</span></div>
                  <em>Severity {alert.severity}</em>
                  <button type="button" onClick={() => resolveAlert(alert.id)}>{alert.status === "RESOLVED" ? "Resolved" : "Resolve"}</button>
                </div>
              ))}
            </div>
            <div className="glass-panel">
              <h2>Audit trail</h2>
              {stats?.audit_logs.slice(0, 8).map((log) => (
                <div className="audit-mini" key={log.id}>
                  <strong>{log.action.replaceAll("_", " ")}</strong>
                  <span>{log.actor_email}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Fraud" && (
          <section className="admin-section-grid">
            <div className="glass-panel">
              <h2>Fraud detection center</h2>
              <p className="ai-explain">This engine reads real audit logs, duplicate vote blocks, failed logins, and turnout signals. It creates an AI alert when risk becomes medium or high.</p>
              <strong className={agent?.risk_level.toLowerCase() === "low" ? "status-good" : "status-warn"}>{agent?.risk_level ?? "Not scanned"}</strong>
              <p>{agent?.summary ?? "Run AI scan to inspect duplicate votes, failed logins, and risk signals."}</p>
              <button className="admin-action" type="button" onClick={runAgentScan}>Run fraud scan</button>
            </div>
            <div className="glass-panel wide">
              <h2>Security events</h2>
              <p className="ai-explain">Security events are ranked by risk score, so the highest-risk activity appears first for admin review.</p>
              {securityEvents.map((event) => (
                <div className="event-row" key={event.id}>
                  <strong>{event.event_type.replaceAll("_", " ")}</strong>
                  <span>{event.description}</span>
                  <em>Risk {event.risk_score}</em>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeTab === "AI Agent" && (
          <section className="admin-section-grid">
            <div className="glass-panel wide">
              <h2>AI Agent dashboard</h2>
              <p className="ai-explain">The agent is not just decoration: it queries verified users, votes, duplicate attempts, failed logins, latest audit logs, and returns risk level plus next actions.</p>
              <p>{agent?.summary ?? "The AI agent monitors election health, fraud risk, and operational readiness."}</p>
              <div className="agent-signal-grid">
                {Object.entries(agent?.signals ?? {}).map(([key, value]) => (
                  <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{value}</strong></div>
                ))}
              </div>
            </div>
            <div className="glass-panel">
              <h2>Recommendations</h2>
              <p className="ai-explain">These recommendations are generated from live election signals and are meant to guide the admin before publishing results.</p>
              {(agent?.recommendations ?? ["Run an AI scan", "Review security alerts", "Verify SMTP before live demo"]).map((item) => (
                <div className="recommendation" key={item}>{item}</div>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Insights" && (
          <section className="admin-section-grid">
            <div className="glass-panel wide">
              <h2>AI Election Insights</h2>
              <p className="ai-explain">Insights convert live database values into admin-friendly metrics: turnout velocity, leader confidence, operational risk, and security posture.</p>
              <div className="insights-grid">
                <div><strong>Turnout velocity</strong><span>{stats?.totals.turnout_percent ?? 0}% participation trend</span></div>
                <div><strong>Winner confidence</strong><span>{topCandidate ? `${topCandidate.name} currently leads` : "Waiting for ballots"}</span></div>
                <div><strong>Operational risk</strong><span>{agent?.risk_level ?? "Run scan for risk score"}</span></div>
                <div><strong>Security posture</strong><span>{alerts.length} active AI alerts</span></div>
              </div>
            </div>
            <div className="glass-panel">
              <h2>Admin Copilot</h2>
              <p className="ai-explain">Copilot summarizes what the admin should check next: SMTP, audit logs, duplicate attempts, security alerts, and result publishing readiness.</p>
              <p>Suggested briefing: verify SMTP, monitor duplicate attempts, export audit logs, and publish results only after the final AI scan.</p>
              <button className="admin-action" type="button" onClick={runAgentScan}>Generate briefing</button>
            </div>
          </section>
        )}

        {activeTab === "DSA Lab" && (
          <section className="glass-panel">
            <h2>DSA Visualizations</h2>
            <div className="dsa-grid">
              {dsaModules.map(([name, purpose, tag], index) => (
                <article key={name}>
                  <div className="dsa-visual" style={{ animationDelay: `${index * 120}ms` }}>
                    <span /><span /><span />
                  </div>
                  <strong>{name}</strong>
                  <p>{purpose}</p>
                  <em>{tag}</em>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Graph" && (
          <section className="admin-section-grid">
            <div className="glass-panel graph-panel wide">
              <h2>Interactive Risk Graph</h2>
              <p className="ai-explain">This graph explains relationships between voter, device, IP address, vote receipt, and AI alert nodes.</p>
              <div className="graph-canvas">
                <span className="node voter">Voter</span>
                <span className="node device">Device</span>
                <span className="node ip">IP</span>
                <span className="node vote">Vote</span>
                <span className="node alert">AI Alert</span>
                <i className="edge e1" /><i className="edge e2" /><i className="edge e3" /><i className="edge e4" />
              </div>
            </div>
            <div className="glass-panel">
              <h2>Graph intelligence</h2>
              <p>User, device, IP, vote, and alert nodes help explain suspicious activity relationships during the exhibition. It is a visual model of fraud investigation flow.</p>
            </div>
          </section>
        )}

        {activeTab === "Timeline" && (
          <section className="glass-panel">
            <h2>Election Timeline Replay</h2>
            <div className="timeline-replay">
              {timelineEvents.map(([time, title, type], index) => (
                <article key={`${time}-${title}`}>
                  <span>{time}</span>
                  <div><strong>{title}</strong><small>{type}</small></div>
                  <i style={{ width: `${(index + 1) * 18}%` }} />
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === "Ledger" && (
          <section className="glass-panel">
            <h2>Blockchain Inspired Vote Ledger</h2>
            <p className="ai-explain">Each block represents an audit milestone. It demonstrates how vote events can be chained through previous hash and current hash values.</p>
            <div className="ledger-chain">
              {ledgerBlocks.map(([block, action, previous, current]) => (
                <article key={block}>
                  <span>{block}</span>
                  <strong>{action}</strong>
                  <small>prev {previous}</small>
                  <small>hash {current}</small>
                </article>
              ))}
            </div>
          </section>
        )}
      </section>
    </main>
  );
}
