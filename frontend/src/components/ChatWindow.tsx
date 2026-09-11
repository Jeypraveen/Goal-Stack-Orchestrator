"use client";

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "@/hooks/useChat";

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (text: string) => void;
}

const SUGGESTIONS = [
  "Book a flight to London",
  "What is Jps.ai?",
  "I need to fly from NYC to Tokyo",
  "How does OrchLLM work?",
];

export default function ChatWindow({ messages, isLoading, onSend }: ChatWindowProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSend(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getRouterLabel = (decision: string | null | undefined) => {
    if (!decision) return null;

    const labels: Record<string, { icon: string; text: string; className: string }> = {
      CONTINUE_CURRENT: { icon: "↪", text: "CONTINUE", className: "" },
      NEW_GOAL_INTERRUPT: { icon: "⚡", text: "NEW GOAL", className: "new-goal" },
      RESUME_PAUSED_GOAL: { icon: "↩️", text: "RESUMED", className: "resume" },
      ABANDON_GOAL: { icon: "✕", text: "ABANDONED", className: "abandon" },
    };

    return labels[decision] || null;
  };

  return (
    <div className="chat-panel">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-logo">G</div>
        <div>
          <div className="chat-header-title">Goal-Stack Orchestrator</div>
          <div className="chat-header-subtitle">
            Multi-goal conversation management
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-container">
            <div className="welcome-icon">🎯</div>
            <div className="welcome-title">Goal-Stack Orchestrator</div>
            <div className="welcome-subtitle">
              Start a conversation! Try booking a flight, then interrupt with a
              question — watch the goal stack manage both seamlessly.
            </div>
            <div className="welcome-suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="suggestion-chip"
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus();
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={`message-row ${msg.role}`}>
                {msg.role === "assistant" && (
                  <div className="message-avatar assistant">G</div>
                )}
                <div>
                  <div className={`message-bubble ${msg.role}`}>
                    {msg.role === "assistant" ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                  </div>
                  {msg.role === "assistant" && msg.router_decision && (() => {
                    const label = getRouterLabel(msg.router_decision);
                    if (!label) return null;
                    return (
                      <div className={`router-label ${label.className}`}>
                        <span>{label.icon}</span>
                        <span>{label.text}</span>
                      </div>
                    );
                  })()}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="typing-indicator">
                <div className="message-avatar assistant">G</div>
                <div className="typing-dots">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-container">
        <div className="input-wrapper">
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            className="send-button"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}
