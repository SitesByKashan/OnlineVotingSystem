"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "../components/AppShell";
import { apiRequest, getToken, VoteReceipt } from "../lib/api";

function formatDate(value?: string) {
  if (!value) return "Not issued yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function ReceiptPage() {
  const [receipt, setReceipt] = useState<VoteReceipt | null>(null);
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<"scan" | "account" | "locked">("locked");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const receiptCode = params.get("code")?.trim();

        if (receiptCode) {
          setMode("scan");
          const response = await apiRequest<{ receipt: VoteReceipt }>(`/votes/receipt/${encodeURIComponent(receiptCode)}`);
          setReceipt(response.receipt);
          return;
        }

        const token = getToken();
        if (!token) {
          setMode("locked");
          setMessage("Please sign in first. Receipts are only shown after a verified user casts a vote.");
          return;
        }

        setMode("account");
        const response = await apiRequest<{ vote: VoteReceipt | null }>("/votes/me/latest", { token });
        if (!response.vote) {
          setMessage("No receipt found yet. Cast your vote first, then your QR receipt will appear here.");
          return;
        }
        setReceipt(response.vote);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Receipt not found.");
      } finally {
        setLoading(false);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const title = mode === "scan" ? "Scanned Vote Receipt" : "My Vote Receipt";

  return (
    <AppShell title={title} subtitle="Dynamic QR verification with election, candidate, and privacy-safe voter proof.">
      {loading && <p className="notice">Loading secure receipt...</p>}
      {!loading && message && !receipt && (
        <section className="receipt-empty-state">
          <span>QR</span>
          <h2>{mode === "locked" ? "Receipt locked" : "No receipt available"}</h2>
          <p>{message}</p>
          <div>
            <Link className="btn primary" href="/signin">Sign in</Link>
            <Link className="btn secondary" href="/vote">Go to voting booth</Link>
          </div>
        </section>
      )}

      {receipt && (
        <section className="receipt-command">
          <div className="receipt-hologram">
            <div className="receipt-orbit one" aria-hidden="true" />
            <div className="receipt-orbit two" aria-hidden="true" />
            <div className="receipt-qr-frame">
              <span className="badge">{mode === "scan" ? "QR scan verified" : "Latest issued receipt"}</span>
              {receipt.qr_png_base64 ? (
                <img className="qr-image" src={`data:image/png;base64,${receipt.qr_png_base64}`} alt="Scannable vote receipt QR code" />
              ) : (
                <div className="receipt-code-fallback">{receipt.receipt_code}</div>
              )}
              <strong>{receipt.receipt_code}</strong>
              <p>Scan this QR to read the verified vote summary directly on mobile.</p>
            </div>
          </div>

          <div className="receipt-summary">
            <span className="badge">Ballot confirmed</span>
            <h2>{receipt.election_title ?? `Election #${receipt.election_id}`}</h2>
            <p>
              Your vote was recorded for <strong>{receipt.name}</strong>. The QR now contains a readable receipt summary instead of a plain link.
            </p>
            <div className="receipt-facts">
              <div><span>Status</span><strong>Valid</strong></div>
              <div><span>Issued at</span><strong>{formatDate(receipt.created_at)}</strong></div>
              <div><span>Election status</span><strong>{receipt.election_status ?? "Recorded"}</strong></div>
              <div><span>Candidate ID</span><strong>#{receipt.candidate_id ?? "N/A"}</strong></div>
            </div>
          </div>
        </section>
      )}

      {receipt && (
        <section className="receipt-proof-grid">
          <article className="receipt-person-card candidate-proof">
            <span className="badge">Voted candidate</span>
            <div className="receipt-person-head">
              {receipt.image_url ? <img src={receipt.image_url} alt={receipt.name ?? "Candidate"} /> : <i>{receipt.name?.slice(0, 2).toUpperCase() ?? "SV"}</i>}
              <div>
                <h2>{receipt.name}</h2>
                <p>{receipt.party}</p>
              </div>
            </div>
            <div className="receipt-manifesto">
              <strong>Manifesto</strong>
              <p>{receipt.manifesto || "Candidate manifesto is not available."}</p>
            </div>
          </article>

          <article className="receipt-person-card voter-proof">
            <span className="badge">Voter proof</span>
            <h2>{receipt.voter_name ?? "Verified voter"}</h2>
            <div className="receipt-identity-list">
              <div><span>Email</span><strong>{receipt.voter_email_masked ?? "Protected"}</strong></div>
              <div><span>CNIC</span><strong>{receipt.voter_cnic_masked ?? "Protected"}</strong></div>
              <div><span>Privacy</span><strong>Masked identity</strong></div>
            </div>
            <p>Full identity stays protected. The receipt proves that one verified ballot was counted for the selected candidate.</p>
          </article>
        </section>
      )}
    </AppShell>
  );
}
