"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { createSession, sendMessage, type ChatResponse, type Goal } from "@/lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  router_decision?: string | null;
  timestamp: Date;
}

export function useChat() {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem("jps_ai_session_id");
    }
    return null;
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [goalStack, setGoalStack] = useState<Goal[]>([]);
  const [activeGoalId, setActiveGoalId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initRef = useRef(false);

  // Initialize session on mount
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    if (sessionId) return; // Already have one from initial state

    createSession()
      .then((session) => {
        setSessionId(session.id);
        sessionStorage.setItem("jps_ai_session_id", session.id);
      })
      .catch((err) => {
        setError(`Failed to create session: ${err.message}`);
      });
  }, [sessionId]);

  const send = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim() || isLoading) return;

      setError(null);

      // Add user message immediately (optimistic)
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const response: ChatResponse = await sendMessage(sessionId, text.trim());

        // Add assistant message
        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.response,
          router_decision: response.router_decision,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Update goal stack
        setGoalStack(response.goal_stack || []);
        setActiveGoalId(response.active_goal_id);
      } catch (err: unknown) {
        let errMsg = err instanceof Error ? err.message : "Unknown error";
        
        // Handle 429 Too Many Requests specifically
        const statusErr = err as { status?: number };
        if (errMsg.includes("429") || statusErr?.status === 429) {
          errMsg = "You're sending messages too fast. Please wait a moment.";
        }
        
        setError(errMsg);
        // Add error message
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: `⚠️ ${errMsg}`,
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, isLoading]
  );

  const resetSession = useCallback(async () => {
    try {
      const session = await createSession();
      setSessionId(session.id);
      sessionStorage.setItem("yellow_ai_session_id", session.id);
      setMessages([]);
      setGoalStack([]);
      setActiveGoalId(null);
      setError(null);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      setError(`Failed to reset: ${errMsg}`);
    }
  }, []);

  return {
    sessionId,
    messages,
    goalStack,
    activeGoalId,
    isLoading,
    error,
    send,
    resetSession,
  };
}
