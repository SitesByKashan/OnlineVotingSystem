"use client";

import { FormEvent, useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, Election, fileToDataUrl, getStoredUser, getToken } from "../lib/api";

type Application = {
  id: number;
  full_name: string;
  party: string;
  status: string;
  created_at: string;
};

export default function ApplyCandidatePage() {
  const [elections, setElections] = useState<Election[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [message, setMessage] = useState("");
  const user = getStoredUser();

  async function load() {
    const token = getToken();
    const [electionData, appData] = await Promise.all([
      apiRequest<{ elections: Election[] }>("/elections"),
      token ? apiRequest<{ applications: Application[] }>("/candidate-applications/me", { token }) : Promise.resolve({ applications: [] }),
    ]);
    setElections(electionData.elections);
    setApplications(appData.applications);
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      load().catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load applications."));
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!getToken()) {
      setMessage("Please sign in before applying as a candidate.");
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const imageFile = form.get("image_file");
    const imageUrl = imageFile instanceof File && imageFile.size > 0 ? await fileToDataUrl(imageFile) : null;
    try {
      await apiRequest<{ message: string }>("/candidate-applications", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({
          election_id: Number(form.get("election_id")),
          full_name: form.get("full_name"),
          party: form.get("party"),
          manifesto: form.get("manifesto"),
          image_url: imageUrl,
          experience: form.get("experience"),
        }),
      });
      formElement.reset();
      await load();
      setMessage("Application submitted. Admin will review it.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Application failed.");
    }
  }

  return (
    <AppShell title="Apply as Candidate" subtitle="Submit your election application for admin review.">
      {message && <p className="notice">{message}</p>}
      <section className="content-grid">
        <form className="panel form-stack" onSubmit={submit}>
          <label>Election<select name="election_id">{elections.map((e) => <option key={e.id} value={e.id}>{e.title}</option>)}</select></label>
          <label>Candidate name<input name="full_name" required minLength={3} defaultValue={user?.full_name ?? ""} /></label>
          <label>Party / Group<input name="party" required minLength={2} /></label>
          <label>Candidate picture<input name="image_file" type="file" accept="image/*" /></label>
          <label>Manifesto<textarea name="manifesto" required minLength={20} /></label>
          <label>Experience<textarea name="experience" required minLength={10} /></label>
          <button type="submit">Submit application</button>
        </form>
        <div className="panel">
          <h2>My applications</h2>
          {applications.map((app) => (
            <div className="list-row" key={app.id}>
              <div><strong>{app.full_name}</strong><span>{app.party}</span></div>
              <em>{app.status}</em>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
