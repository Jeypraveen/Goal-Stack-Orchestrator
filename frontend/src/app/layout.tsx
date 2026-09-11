import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Goal-Stack Orchestrator | Multi-Goal Conversation AI",
  description:
    "A conversational AI backend that manages multiple concurrent user goals as a persistent stack — supporting mid-conversation interruption, topic switching, and resumption without context loss.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
