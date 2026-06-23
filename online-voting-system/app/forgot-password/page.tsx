"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import BrandLogo from "../components/BrandLogo";
import { apiRequest } from "../lib/api";

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [devOtp, setDevOtp] = useState("");
  const [step, setStep] = useState<"request" | "reset">("request");

  async function requestOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiRequest<{ message: string; email: string; dev_otp?: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email") }),
      });
      localStorage.setItem("smartvote_reset_email", response.email);
      setMessage(response.message);
      if (response.dev_otp) setDevOtp(response.dev_otp);
      setStep("reset");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to send OTP.");
    }
  }

  async function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiRequest<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          otp: form.get("otp"),
          new_password: form.get("new_password"),
        }),
      });
      setMessage(response.message);
      window.setTimeout(() => { window.location.href = "/signin"; }, 900);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reset failed.");
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-visual">
        <Link className="logo" href="/"><BrandLogo /></Link>
        <h1>Reset access securely.</h1>
        <p>Forgot password uses the same OTP security channel as email verification.</p>
      </section>
      <section className="auth-card">
        <span className="badge">Password recovery</span>
        <h2>{step === "request" ? "Send reset OTP" : "Set new password"}</h2>
        {step === "request" ? (
          <form className="form-stack" onSubmit={requestOtp}>
            <label>Email<input name="email" type="email" required placeholder="you@example.com" /></label>
            <button type="submit">Send OTP</button>
          </form>
        ) : (
          <form className="form-stack" onSubmit={resetPassword}>
            <label>Email<input name="email" type="email" required defaultValue={typeof window === "undefined" ? "" : localStorage.getItem("smartvote_reset_email") ?? ""} /></label>
            <label>OTP<input name="otp" required pattern="[0-9]{6}" inputMode="numeric" /></label>
            <label>New password<input name="new_password" type="password" required minLength={5} /></label>
            <button type="submit">Reset password</button>
          </form>
        )}
        {message && <p className="notice">{message}</p>}
        {devOtp && <p className="notice warning">Development OTP: <strong>{devOtp}</strong></p>}
        <div className="auth-links"><Link href="/signin">Back to sign in</Link></div>
      </section>
    </main>
  );
}
