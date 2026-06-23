"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiUser, getStoredUser } from "../lib/api";

export function HomeNavActions() {
  const [user, setUser] = useState<ApiUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  if (user) {
    return (
      <div className="home-session">
        <Link href="/candidates">Candidates</Link>
        <Link href="/dashboard">Dashboard</Link>
        <span>{user.full_name}</span>
      </div>
    );
  }

  return (
    <div>
      <Link href="/candidates">Candidates</Link>
      <Link href="/signin">Sign in</Link>
      <Link className="nav-cta" href="/signup">Get started</Link>
    </div>
  );
}

export function HomeHeroActions() {
  const [user, setUser] = useState<ApiUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  if (user) {
    return (
      <div className="hero-actions">
        <Link className="btn primary" href="/dashboard">Open voter dashboard</Link>
        <Link className="btn secondary" href="/vote">Live voting booth</Link>
      </div>
    );
  }

  return (
    <div className="hero-actions">
      <Link className="btn primary" href="/signup">Create voter account</Link>
      <Link className="btn secondary" href="/signin">Open dashboard</Link>
    </div>
  );
}
