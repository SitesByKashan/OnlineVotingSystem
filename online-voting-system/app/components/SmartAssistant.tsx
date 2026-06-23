"use client";

import { FormEvent, useState } from "react";
import { apiRequest, getToken } from "../lib/api";

type Message = {
  role: "assistant" | "user";
  text: string;
};

type ChatResponse = {
  reply: string;
  agent: {
    actions: string[];
    mode: string;
  };
};

export default function SmartAssistant() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actions, setActions] = useState(["Live results", "QR receipt scan", "AI fraud monitor"]);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hi, I am SmartVote AI Agent. I can guide voters, explain live results, verify receipt flow, and monitor election security signals.",
    },
  ]);

  async function submit(message: string) {
    const clean = message.trim();
    if (!clean) return;
    setMessages((current) => [...current, { role: "user", text: clean }]);
    setLoading(true);
    try {
      const [response] = await Promise.all([
        apiRequest<ChatResponse>("/ai/chat", {
        method: "POST",
        token: getToken(),
        body: JSON.stringify({
          message: clean,
          page: typeof window === "undefined" ? "unknown" : window.location.pathname,
        }),
        }),
        new Promise((resolve) => window.setTimeout(resolve, 1300)),
      ]);
      setMessages((current) => [...current, { role: "assistant", text: response.reply }]);
      setActions(response.agent.actions);
    } catch {
      setMessages((current) => [
        ...current,
        { role: "assistant", text: "I cannot reach the AI backend. Start FastAPI on port 8010 and try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const message = String(data.get("message") ?? "");
    form.reset();
    submit(message);
  }

  return (
    <div className="ai-widget">
      {open && (
        <section className="ai-panel" aria-label="SmartVote AI chatbot">
          <header>
            <span>AI</span>
            <div>
              <strong>SmartVote AI Agent</strong>
              <small>{loading ? "Thinking..." : "Live guardian monitoring"}</small>
            </div>
          </header>
          <div className="ai-messages">
            {messages.map((message, index) => (
              <p className={message.role} key={`${message.role}-${index}`}>{message.text}</p>
            ))}
            {loading && (
              <p className="assistant typing">
                <span /><span /><span />
              </p>
            )}
          </div>
          <div className="ai-suggestions">
            {actions.map((action) => (
              <button type="button" key={action} onClick={() => submit(action)}>
                {action}
              </button>
            ))}
          </div>
          <form onSubmit={handleSubmit}>
            <input name="message" placeholder="Ask SmartVote AI..." autoComplete="off" />
            <button type="submit" disabled={loading}>Send</button>
          </form>
        </section>
      )}
      <button className="ai-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        {open ? "Close" : "AI Chat"}
      </button>
    </div>
  );
}
