/**
 * API client for the Jps.ai backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Session {
  id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface Goal {
  id: string;
  session_id: string;
  intent_type: string;
  status: "active" | "paused" | "completed" | "abandoned";
  slots_filled: Record<string, string | number>;
  slots_missing: string[];
  stack_position: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ChatResponse {
  response: string;
  goal_stack: Goal[];
  active_goal_id: string | null;
  router_decision: string | null;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  goal_id: string | null;
  router_decision: string | null;
  created_at: string;
}

/**
 * Create a new conversation session.
 */
export async function createSession(): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
  return res.json();
}

/**
 * Send a chat message and get a response + updated goal stack.
 */
export async function sendMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Chat failed: ${res.status} — ${detail}`);
  }
  return res.json();
}

/**
 * Get the current goal stack for a session.
 */
export async function getGoalStack(
  sessionId: string
): Promise<{ goals: Goal[]; active_goal: Goal | null }> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/goals`);
  if (!res.ok) throw new Error(`Failed to fetch goals: ${res.status}`);
  return res.json();
}

/**
 * Get conversation history for a session.
 */
export async function getMessages(
  sessionId: string,
  limit = 50
): Promise<Message[]> {
  const res = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/messages?limit=${limit}`
  );
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
  return res.json();
}
