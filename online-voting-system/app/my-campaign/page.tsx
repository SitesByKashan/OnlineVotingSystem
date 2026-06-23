"use client";

import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, getToken } from "../lib/api";

type Campaign = {
  candidate_id: number;
  election_id: number;
  election_title: string;
  election_status: string;
  name: string;
  party: string;
  image_url?: string | null;
  votes: number;
  election_total_votes: number;
  vote_share: number;
  anonymous_votes: Array<{ receipt: string; created_at: string }>;
};

export default function MyCampaignPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        if (!getToken()) {
          setMessage("Please sign in to view your campaign results.");
          return;
        }
        const response = await apiRequest<{ campaigns: Campaign[] }>("/candidate-results/me", { token: getToken() });
        setCampaigns(response.campaigns);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Unable to load campaign results.");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <AppShell title="My Campaign Results" subtitle="Election-wise candidate analytics for approved candidates.">
      {message && <p className="notice warning">{message}</p>}
      {!message && campaigns.length === 0 && (
        <p className="notice">This page becomes active after admin accepts your candidate application.</p>
      )}
      <section className="campaign-grid">
        {campaigns.map((campaign) => (
          <article className="campaign-card" key={`${campaign.election_id}-${campaign.candidate_id}`}>
            <div className="campaign-orbit" aria-hidden="true" />
            <div className="campaign-card-inner">
              <div className="campaign-head">
                <div className="campaign-avatar-wrap">
                  {campaign.image_url ? <img src={campaign.image_url} alt={campaign.name} /> : <span>{campaign.name.slice(0, 2).toUpperCase()}</span>}
                  <i aria-hidden="true" />
                </div>
                <div>
                  <small>{campaign.party}</small>
                  <h2>{campaign.name}</h2>
                  <p>{campaign.election_title} - {campaign.election_status}</p>
                  <div className="campaign-badges">
                    <span>Live result feed</span>
                    <span>Secret ballot safe</span>
                    <span>Election #{campaign.election_id}</span>
                  </div>
                </div>
              </div>
              <div className="campaign-body">
                <div className="campaign-result-core">
                  <div className="campaign-meter" style={{ "--score": `${Math.min(campaign.vote_share, 100)}%` } as CSSProperties}>
                    <span>{campaign.vote_share}%</span>
                    <em>vote share</em>
                  </div>
                  <div className="campaign-stats">
                    <div><strong>{campaign.votes}</strong><span>Your votes</span></div>
                    <div><strong>{campaign.election_total_votes}</strong><span>Election votes</span></div>
                    <div><strong>{campaign.anonymous_votes.length}</strong><span>Verified receipts</span></div>
                  </div>
                </div>
                <div className="vote-proof-panel">
                  <div>
                    <h3>Anonymous vote proofs</h3>
                    <p>Secret ballot protected: voter identities are hidden, receipts prove votes were counted.</p>
                  </div>
                  <div className="receipt-rail">
                    {campaign.anonymous_votes.map((vote) => (
                      <div className="receipt-chip" key={vote.receipt}>
                        <strong>{vote.receipt}</strong>
                        <span>{vote.created_at}</span>
                        <em>Counted</em>
                      </div>
                    ))}
                    {campaign.anonymous_votes.length === 0 && <p>No votes received yet.</p>}
                  </div>
                </div>
              </div>
            </div>
          </article>
        ))}
      </section>
    </AppShell>
  );
}
