"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, Candidate, Election } from "../lib/api";

export default function CandidatesPage() {
  const [elections, setElections] = useState<Election[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [activeElection, setActiveElection] = useState(1);

  async function loadCandidates(electionId: number) {
    const response = await apiRequest<{ candidates: Candidate[] }>(`/elections/${electionId}/candidates`);
    setCandidates(response.candidates);
  }

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      const electionData = await apiRequest<{ elections: Election[] }>("/elections");
      setElections(electionData.elections);
      const active = electionData.elections.find((item) => item.status === "ACTIVE") ?? electionData.elections[0];
      if (active) {
        setActiveElection(active.id);
        await loadCandidates(active.id);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <AppShell title="Candidates" subtitle="Review candidate profiles before entering the voting flow.">
      <div className="toolbar">
        <select value={activeElection} onChange={(event) => { const id = Number(event.target.value); setActiveElection(id); loadCandidates(id); }}>
          {elections.map((election) => <option key={election.id} value={election.id}>{election.title}</option>)}
        </select>
      </div>
      <section className="candidate-cards">
        {candidates.map((candidate) => (
          <article key={candidate.id}>
            {candidate.image_url ? (
              <img className="candidate-photo" src={candidate.image_url} alt={candidate.name} />
            ) : (
              <span className={`orb ${candidate.color}`} />
            )}
            <small>{candidate.party}</small>
            <h2>{candidate.name}</h2>
            <p>{candidate.manifesto}</p>
            <Link className="btn secondary" href={`/candidate-profile?id=${candidate.id}`}>Open profile</Link>
          </article>
        ))}
      </section>
    </AppShell>
  );
}
