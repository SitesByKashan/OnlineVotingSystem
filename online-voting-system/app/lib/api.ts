export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8010";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export type ApiUser = {
  id: number;
  full_name: string;
  email: string;
  cnic?: string | null;
  role: "VOTER" | "ADMIN" | "SUPER_ADMIN";
  is_verified: boolean;
  is_blocked?: boolean;
};

export type Election = {
  id: number;
  title: string;
  description: string;
  status: "DRAFT" | "ACTIVE" | "PAUSED" | "CLOSED" | "PUBLISHED";
  start_time?: string;
  end_time?: string;
};

export type Candidate = {
  id: number;
  election_id: number;
  name: string;
  party: string;
  manifesto: string;
  image_url?: string | null;
  color: string;
};

export type VoteReceipt = {
  receipt_code: string;
  receipt_qr_payload: string;
  qr_png_base64?: string;
  election_id?: number;
  candidate_id?: number;
  election_title?: string;
  election_status?: string;
  created_at: string;
  name?: string;
  party?: string;
  manifesto?: string;
  image_url?: string | null;
  voter_name?: string;
  voter_email_masked?: string;
  voter_cnic_masked?: string;
};

export type LeaderboardRow = {
  id: number;
  name: string;
  party: string;
  votes: number;
};

export type ApiOptions = RequestInit & { token?: string };

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail ?? "Request failed. Please try again.");
  }

  return data as T;
}

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("smartvote_token") ?? "";
}

export function getStoredUser(): ApiUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("smartvote_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ApiUser;
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: ApiUser): void {
  localStorage.setItem("smartvote_token", token);
  localStorage.setItem("smartvote_user", JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem("smartvote_token");
  localStorage.removeItem("smartvote_user");
}

export function roleHome(user: ApiUser): string {
  return user.role === "VOTER" ? "/dashboard" : "/admin";
}

export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Could not read image file."));
    reader.readAsDataURL(file);
  });
}
