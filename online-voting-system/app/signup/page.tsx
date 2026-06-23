"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import BrandLogo from "../components/BrandLogo";
import { apiRequest } from "../lib/api";

export default function SignupPage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const form = new FormData(event.currentTarget);

    try {
      const response = await apiRequest<{ message: string; email: string; email_sent: boolean; dev_otp?: string }>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          full_name: form.get("full_name"),
          email: form.get("email"),
          cnic: form.get("cnic"),
          password: form.get("password"),
        }),
      });
      localStorage.setItem("smartvote_email", response.email);
      setMessage(response.email_sent ? "OTP sent to your email. Check inbox and verify." : "SMTP is not configured yet. Ask admin to configure SMTP for real email OTP.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-visual">
        <Link className="logo" href="/"><BrandLogo /></Link>
        <h1>Create a verified voter identity.</h1>
        <p>Every account is protected with SMTP OTP verification before voting is unlocked.</p>
      </section>
      <section className="auth-card">
        <span className="badge">Signup</span>
        <h2>Start voting securely</h2>
        <form className="form-stack" onSubmit={submit}>
          <label>Full name<input name="full_name" required minLength={3} placeholder="Your name" /></label>
          <label>Email<input name="email" type="email" required placeholder="you@example.com" /></label>
          <label>CNIC number<input name="cnic" required pattern="\d{5}-?\d{7}-?\d{1}" placeholder="42101-1234567-1" /></label>
          <label>Password<input name="password" type="password" required minLength={5} placeholder="Minimum 5 characters" /></label>
          <button type="submit" disabled={loading}>{loading ? "Sending OTP..." : "Create account"}</button>
        </form>
        {message && <p className="notice">{message}</p>}
        <div className="auth-links">
          <Link href="/verify-email">Verify OTP</Link>
          <Link href="/signin">Already have an account?</Link>
        </div>
      </section>
    </main>
  );
}
