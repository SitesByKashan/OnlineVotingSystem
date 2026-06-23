"use client";

import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { apiRequest, getToken } from "../lib/api";

type Notification = {
  id: number;
  title: string;
  message: string;
  type: string;
  created_at: string;
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const data = await apiRequest<{ notifications: Notification[] }>("/notifications/me", { token: getToken() });
        setNotifications(data.notifications);
      } catch {
        setMessage("Notifications are available after sign in.");
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <AppShell title="Notifications" subtitle="Live election, application and security updates.">
      {message && <p className="notice warning">{message}</p>}
      <section className="panel">
        {notifications.map((item) => (
          <div className="notification-row" key={item.id}>
            <strong>{item.title}</strong>
            <span>{item.message}</span>
            <em>{item.type}</em>
          </div>
        ))}
      </section>
    </AppShell>
  );
}
