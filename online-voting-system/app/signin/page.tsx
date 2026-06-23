"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import BrandLogo from "../components/BrandLogo";
import { apiRequest, ApiUser, roleHome, saveSession } from "../lib/api";

export default function SigninPage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const form = new FormData(event.currentTarget);

    try {
      const response = await apiRequest<{ access_token: string; user: ApiUser }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      saveSession(response.access_token, response.user);
      window.location.href = roleHome(response.user);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Signin failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-visual">
        <Link className="logo" href="/"><BrandLogo /></Link>
        <h1>Access your election workspace.</h1>
        <p>Voters enter the dashboard. Admins are routed into the control center.</p>
      </section>
      <section className="auth-card">
        <span className="badge">Secure login</span>
        <h2>Welcome back</h2>
        <form className="form-stack" onSubmit={submit}>
          <label>Email<input name="email" type="email" required placeholder="you@example.com" /></label>
          <label>Password<input name="password" type="password" required placeholder="Your password" /></label>
          <button type="submit" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
        </form>
        {message && <p className="notice warning">{message}</p>}
        <div className="auth-links">
          <Link href="/signup">Create account</Link>
          <Link href="/forgot-password">Forgot password?</Link>
        </div>
      </section>
    </main>
  );
}
