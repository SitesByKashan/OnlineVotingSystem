"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import BrandLogo from "../components/BrandLogo";
import { apiRequest } from "../lib/api";

export default function VerifyEmailPage() {
  const [email, setEmail] = useState(() => (typeof window === "undefined" ? "" : localStorage.getItem("smartvote_email") ?? ""));
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const form = new FormData(event.currentTarget);

    try {
      const response = await apiRequest<{ message: string }>("/auth/verify-email", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), otp: form.get("otp") }),
      });
      setMessage(response.message);
      window.setTimeout(() => { window.location.href = "/signin"; }, 800);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "OTP verification failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-visual">
        <Link className="logo" href="/"><BrandLogo /></Link>
        <h1>Verify your email OTP.</h1>
        <p>Enter the 6 digit code sent by SMTP email. Local demo mode also displays the OTP after signup.</p>
      </section>
      <section className="auth-card">
        <span className="badge">Email OTP</span>
        <h2>Unlock your account</h2>
        <form className="form-stack" onSubmit={submit}>
          <label>Email<input name="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>OTP<input name="otp" required pattern="[0-9]{6}" inputMode="numeric" placeholder="123456" /></label>
          <button type="submit" disabled={loading}>{loading ? "Verifying..." : "Verify email"}</button>
        </form>
        {message && <p className="notice">{message}</p>}
        <div className="auth-links">
          <Link href="/signup">Back to signup</Link>
          <Link href="/signin">Sign in</Link>
        </div>
      </section>
    </main>
  );
}
