"use client";

import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, Candidate, Election, getStoredUser, getToken } from "../lib/api";

export default function VotePage() {
  const [elections, setElections] = useState<Election[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [electionId, setElectionId] = useState(1);
  const [selected, setSelected] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  async function loadElection(id: number) {
    setElectionId(id);
    const response = await apiRequest<{ candidates: Candidate[] }>(`/elections/${id}/candidates`);
    setCandidates(response.candidates);
    setSelected(null);
  }

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const response = await apiRequest<{ elections: Election[] }>("/elections");
        setElections(response.elections);
        const active = response.elections.find((item) => item.status === "ACTIVE") ?? response.elections[0];
        if (active) await loadElection(active.id);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Unable to load voting flow.");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function castVote() {
    const user = getStoredUser();
    if (!selected) {
      setMessage("Select a candidate first.");
      return;
    }
    if (!getToken()) {
      setMessage("Please sign in before casting a vote.");
      return;
    }
    if (user?.role !== "VOTER") {
      setMessage("Admin accounts can monitor elections but cannot cast votes.");
      return;
    }
    try {
      const response = await apiRequest<{ receipt_code: string; qr_payload: string; qr_png_base64?: string }>("/votes", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({ election_id: electionId, candidate_id: selected, device_hash: "browser-demo-device" }),
      });
      localStorage.setItem("smartvote_last_receipt", response.receipt_code);
      localStorage.setItem("smartvote_last_qr", response.qr_payload);
      if (response.qr_png_base64) localStorage.setItem("smartvote_last_qr_png", response.qr_png_base64);
      window.location.href = `/receipt?code=${encodeURIComponent(response.receipt_code)}`;
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Vote failed.";
      if (detail.toLowerCase().includes("already voted")) {
        try {
          const existing = await apiRequest<{ vote: { receipt_code: string } | null }>(`/votes/me/${electionId}`, { token: getToken() });
          if (existing.vote?.receipt_code) {
            window.location.href = `/receipt?code=${encodeURIComponent(existing.vote.receipt_code)}`;
            return;
          }
        } catch {
          setMessage(detail);
          return;
        }
      }
      setMessage(detail);
    }
  }

  return (
    <AppShell title="Voting Flow" subtitle="Select the active election, choose a candidate, and receive a QR receipt.">
      {message && <p className="notice warning">{message}</p>}
      <div className="toolbar">
        <select value={electionId} onChange={(event) => loadElection(Number(event.target.value))}>
          {elections.map((election) => <option key={election.id} value={election.id}>{election.title} - {election.status}</option>)}
        </select>
      </div>
      <section className="vote-flow">
        <div className="flow-steps">
          <span className="done">1. Verified session</span>
          <span className={selected ? "done" : ""}>2. Candidate selected</span>
          <span>3. Receipt generated</span>
        </div>
        <div className="candidate-cards selectable">
          {candidates.map((candidate) => (
            <button className={selected === candidate.id ? "selected" : ""} type="button" key={candidate.id} onClick={() => setSelected(candidate.id)}>
              {candidate.image_url ? (
                <img className="candidate-photo" src={candidate.image_url} alt={candidate.name} />
              ) : (
                <span className={`orb ${candidate.color}`} />
              )}
              <small>{candidate.party}</small>
              <strong>{candidate.name}</strong>
              <p>{candidate.manifesto}</p>
            </button>
          ))}
        </div>
        <button className="btn primary full" type="button" onClick={castVote}>Cast encrypted vote</button>
      </section>
    </AppShell>
  );
}
