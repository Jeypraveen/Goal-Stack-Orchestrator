"use client";

import ChatWindow from "@/components/ChatWindow";
import GoalStackSidebar from "@/components/GoalStackSidebar";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const {
    messages,
    goalStack,
    activeGoalId,
    isLoading,
    error,
    send,
  } = useChat();

  return (
    <div className="app-container">
      {error && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-full text-sm font-medium animate-fade-in z-50">
          {error}
        </div>
      )}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSend={send}
      />
      <GoalStackSidebar
        goals={goalStack}
        activeGoalId={activeGoalId}
      />
    </div>
  );
}
