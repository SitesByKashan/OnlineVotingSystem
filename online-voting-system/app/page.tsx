import Link from "next/link";
import BrandLogo from "./components/BrandLogo";
import { HomeHeroActions, HomeNavActions } from "./components/HomeSession";

const stats = [
  ["JWT", "Secure sessions"],
  ["OTP", "SMTP verification"],
  ["1 vote", "Per election"],
  ["Live", "WebSocket results"],
];

const features = [
  ["AI Chatbot", "Voter guidance for OTP, eligibility, vote flow, and receipts."],
  ["Fraud Monitoring", "Duplicate votes, failed logins, and suspicious activity alerts."],
  ["QR Receipt", "A verifiable receipt code and QR payload after successful voting."],
  ["Admin Copilot", "Election health, analytics, and security recommendations."],
];

const startupModules = [
  "3D Election Command Center",
  "AI Fraud Detection Engine",
  "DSA Visualization Lab",
  "Vote Ledger Replay",
  "Interactive Risk Graph",
  "Real-Time Analytics",
];

export default function LandingPage() {
  return (
    <main className="site-page">
      <nav className="topbar">
        <Link className="logo" href="/"><BrandLogo /></Link>
        <HomeNavActions />
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <span className="badge">AI Powered Online Voting System</span>
          <h1>Secure digital elections with AI monitoring and live results.</h1>
          <p>
            SmartVote combines OTP verified identities, JWT sessions, one-user-one-vote enforcement,
            QR receipts, real-time leaderboards, and an AI assistant in one modern SaaS platform.
          </p>
          <HomeHeroActions />
        </div>

        <div className="hero-product" aria-label="SmartVote product preview">
          <span className="hero-satellite sat-a">Smart</span>
          <span className="hero-satellite sat-b">Voting</span>
          <span className="hero-satellite sat-c">System</span>
          <span className="hero-depth-ring depth-one" />
          <span className="hero-depth-ring depth-two" />
          <div className="product-window">
            <span className="window-glow-line line-one" />
            <span className="window-glow-line line-two" />
            <div className="window-head"><span /><span /><span /></div>
            <div className="result-card elevated">
              <small>Live election</small>
              <strong>SSUET Student Council</strong>
              <div className="progress-line"><i style={{ width: "68%" }} /></div>
            </div>
            <div className="mini-grid">
              <div><strong>1,284</strong><span>Verified voters</span></div>
              <div><strong>72%</strong><span>Turnout</span></div>
              <div><strong>Low</strong><span>AI risk</span></div>
              <div><strong>3</strong><span>Candidates</span></div>
            </div>
            <div className="hero-ledger">
              <span>Vote hash</span>
              <strong>0xA91F...CF31</strong>
              <small>Receipt verified live</small>
            </div>
          </div>
        </div>
      </section>

      <section className="stat-strip">
        {stats.map(([value, label]) => (
          <div key={label}><strong>{value}</strong><span>{label}</span></div>
        ))}
      </section>

      <section className="feature-section">
        <div className="section-heading">
          <span className="badge">Exhibition ready</span>
          <h2>Everything needed for a polished voting demo.</h2>
        </div>
        <div className="feature-grid">
          {features.map(([title, body]) => (
            <article key={title}>
              <span className="feature-icon">{title.slice(0, 2)}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="startup-section">
        <div className="section-heading">
          <span className="badge">Startup-grade platform</span>
          <h2>Built to feel like a real election intelligence product.</h2>
        </div>
        <div className="startup-grid">
          <div className="startup-command-preview">
            <span className="preview-ring one" />
            <span className="preview-ring two" />
            <div className="preview-core">SV</div>
          </div>
          <div className="startup-module-list">
            {startupModules.map((module) => (
              <article key={module}>
                <strong>{module}</strong>
                <span>Available in the premium admin console</span>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
