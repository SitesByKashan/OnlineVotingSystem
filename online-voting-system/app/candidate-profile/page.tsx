"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, Candidate } from "../lib/api";

export default function CandidateProfilePage() {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const id = params.get("id");
        if (!id) {
          setMessage("Candidate ID missing.");
          return;
        }
        const data = await apiRequest<{ candidate: Candidate }>(`/candidates/${id}`);
        setCandidate(data.candidate);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Candidate not found.");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <AppShell title={candidate?.name ?? "Candidate Profile"} subtitle="Review manifesto, party and election details before voting.">
      {message && <p className="notice warning">{message}</p>}
      {candidate && (
        <section className="candidate-detail-hero">
          <div>
            {candidate.image_url ? (
              <img className="candidate-detail-photo" src={candidate.image_url} alt={candidate.name} />
            ) : (
              <span className={`orb ${candidate.color}`} />
            )}
            <small>{candidate.party}</small>
            <h2>{candidate.name}</h2>
            <p>{candidate.manifesto}</p>
            <div className="hero-actions">
              <Link className="btn primary" href="/vote">Vote now</Link>
              <Link className="btn secondary" href="/candidates">Back to candidates</Link>
            </div>
          </div>
          <div className="candidate-promise-card">
            <strong>Candidate intelligence</strong>
            <span>Election ID #{candidate.election_id}</span>
            <span>Manifesto reviewed by AI assistant</span>
            <span>Eligible for active election ballot</span>
          </div>
        </section>
      )}
    </AppShell>
  );
}
