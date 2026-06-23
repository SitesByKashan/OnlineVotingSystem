"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";
import { apiRequest, ApiUser, clearSession, getStoredUser, getToken } from "../lib/api";
import BrandLogo from "./BrandLogo";

type AppShellProps = {
  children: ReactNode;
  title: string;
  subtitle: string;
};

export default function AppShell({ children, title, subtitle }: AppShellProps) {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [hasCampaign, setHasCampaign] = useState(false);

  useEffect(() => {
    const currentUser = getStoredUser();
    setUser(currentUser);
    if (currentUser?.role === "VOTER" && getToken()) {
      apiRequest<{ campaigns: unknown[] }>("/candidate-results/me", { token: getToken() })
        .then((data) => setHasCampaign(data.campaigns.length > 0))
        .catch(() => setHasCampaign(false));
    }
  }, []);

  function logout() {
    clearSession();
    window.location.href = "/";
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <Link className="logo" href="/"><BrandLogo /></Link>
        <nav>
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/candidates">Candidates</Link>
          {user?.role === "VOTER" && <Link href="/apply-candidate">Apply</Link>}
          {hasCampaign && <Link href="/my-campaign">My Campaign</Link>}
          {user?.role === "VOTER" && <Link href="/vote">Vote</Link>}
          <Link href="/receipt">Receipt</Link>
          <Link href="/notifications">Notifications</Link>
          {user?.email.toLowerCase() === "admin@gmail.com" && <Link href="/admin">Admin</Link>}
        </nav>
      </aside>
      <section className="workspace">
        <header className="workspace-header">
          <div>
            <span className="badge">{user ? user.role : "Guest"}</span>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <div className="user-chip">
            <span>{user?.full_name ?? "Not signed in"}</span>
            {user ? <button type="button" onClick={logout}>Logout</button> : <Link href="/signin">Sign in</Link>}
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}
