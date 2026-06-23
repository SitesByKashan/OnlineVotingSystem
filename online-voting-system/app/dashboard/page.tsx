"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, Election, getStoredUser, getToken, LeaderboardRow, VoteReceipt, WS_BASE } from "../lib/api";

export default function DashboardPage() {
  const [elections, setElections] = useState<Election[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [vote, setVote] = useState<VoteReceipt | null>(null);
  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null);
  const [liveVotes, setLiveVotes] = useState(0);
  const [activeElectionId, setActiveElectionId] = useState<number | null>(null);
  const [agentStatus, setAgentStatus] = useState("Monitoring identity, duplicate vote attempts, and live turnout.");
  const [message, setMessage] = useState("");

  useEffect(() => {
    setUser(getStoredUser());
    const timer = window.setTimeout(async () => {
      try {
        const electionData = await apiRequest<{ elections: Election[] }>("/elections");
        setElections(electionData.elections);
        const active = electionData.elections.find((item) => item.status === "ACTIVE") ?? electionData.elections[0];
        if (active) {
          setActiveElectionId(active.id);
          const board = await apiRequest<{ results: LeaderboardRow[] }>(`/elections/${active.id}/leaderboard`);
          setLeaderboard(board.results);
          setLiveVotes(board.results.reduce((total, row) => total + row.votes, 0));
          if (getToken()) {
            const voteData = await apiRequest<{ vote: VoteReceipt | null }>(`/votes/me/${active.id}`, { token: getToken() });
            setVote(voteData.vote);
          }
        }
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Unable to load dashboard.");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!activeElectionId) return;
    const voteSocket = new WebSocket(`${WS_BASE}/ws/votes/${activeElectionId}`);
    const boardSocket = new WebSocket(`${WS_BASE}/ws/leaderboard/${activeElectionId}`);

    voteSocket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "VOTE_COUNT") setLiveVotes(payload.total_votes);
      if (payload.type === "VOTE_CAST") setAgentStatus("AI monitor: new vote accepted, fraud signals recalculating live.");
    };
    boardSocket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "LEADERBOARD") {
        setLeaderboard(payload.results);
        setLiveVotes(payload.results.reduce((total: number, row: LeaderboardRow) => total + row.votes, 0));
      }
    };

    return () => {
      voteSocket.close();
      boardSocket.close();
    };
  }, [activeElectionId]);

  return (
    <AppShell title="Voter Dashboard" subtitle="Track active elections, receipt status, and live rankings.">
      {message && <p className="notice warning">{message}</p>}
      <section className="dashboard-cards">
        <article><span>Account</span><strong>{user?.is_verified ? "Verified" : "Needs OTP"}</strong><p>{user?.email ?? "Sign in to vote"}</p></article>
        <article><span>Active elections</span><strong>{elections.filter((item) => item.status === "ACTIVE").length}</strong><p>{elections.length} total elections</p></article>
        <article><span>Vote receipt</span><strong>{vote ? "Issued" : "Pending"}</strong><p>{vote?.receipt_code ?? "No vote cast yet"}</p></article>
        <article><span>Live votes</span><strong>{liveVotes}</strong><p>WebSocket leaderboard online</p></article>
      </section>
      <section className="content-grid">
        <div className="panel">
          <h2>Available elections</h2>
          {elections.map((election) => (
            <div className="list-row" key={election.id}>
              <div><strong>{election.title}</strong><span>{election.description}</span></div>
              <em>{election.status}</em>
            </div>
          ))}
          {user?.role === "VOTER" ? (
            <Link className="btn primary" href="/vote">Start voting flow</Link>
          ) : (
            <p className="notice">Admin monitoring mode: voting actions are disabled for this account.</p>
          )}
        </div>
        <div className="panel">
          <h2>Live leaderboard</h2>
          {leaderboard.map((row) => (
            <div className="leader-row" key={row.id}>
              <span>{row.name}</span>
              <i style={{ width: `${Math.max(liveVotes ? (row.votes / liveVotes) * 100 : 8, 8)}%` }} />
              <strong>{row.votes} votes</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="content-grid">
        <div className="panel ai-monitor-card">
          <span className="badge">AI Monitoring</span>
          <h2>Election guardian agent</h2>
          <p>{agentStatus}</p>
          <div className="agent-metrics">
            <div><strong>Low</strong><span>Fraud risk</span></div>
            <div><strong>Live</strong><span>Vote stream</span></div>
            <div><strong>Active</strong><span>Receipt verifier</span></div>
          </div>
        </div>
        <div className="panel">
          <h2>Result visibility</h2>
          {leaderboard.map((row, index) => (
            <div className="list-row" key={`rank-${row.id}`}>
              <div><strong>#{index + 1} {row.name}</strong><span>{row.party}</span></div>
              <em>{liveVotes ? Math.round((row.votes / liveVotes) * 100) : 0}%</em>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
