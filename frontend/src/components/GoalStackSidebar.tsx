"use client";

import type { Goal } from "@/lib/api";

interface GoalStackSidebarProps {
  goals: Goal[];
  activeGoalId: string | null;
}

const INTENT_ICONS: Record<string, string> = {
  booking: "✈️",
  faq: "❓",
};

export default function GoalStackSidebar({ goals, activeGoalId }: GoalStackSidebarProps) {
  // Sort: active first, then by stack_position descending
  const sortedGoals = [...goals].sort((a, b) => {
    if (a.status === "active" && b.status !== "active") return -1;
    if (b.status === "active" && a.status !== "active") return 1;
    return b.stack_position - a.stack_position;
  });

  const activeCount = goals.filter(
    (g) => g.status === "active" || g.status === "paused"
  ).length;

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-title">
          <span className="sidebar-title-icon">📚</span>
          Goal Stack
        </div>
        {activeCount > 0 && (
          <span className="sidebar-count">{activeCount} active</span>
        )}
      </div>

      {/* Content */}
      <div className="sidebar-content">
        {sortedGoals.length === 0 ? (
          <div className="sidebar-empty">
            <div className="sidebar-empty-icon">📭</div>
            <div className="sidebar-empty-text">
              No goals yet.
              <br />
              Start a conversation to see the goal stack in action.
            </div>
          </div>
        ) : (
          sortedGoals.map((goal, index) => (
            <div key={goal.id}>
              <GoalCard goal={goal} isActive={goal.id === activeGoalId} />
              {index < sortedGoals.length - 1 && (
                <div className="stack-indicator">
                  <div className="stack-connector" />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// =========================================================================
// Goal Card sub-component
// =========================================================================

function GoalCard({ goal, isActive }: { goal: Goal; isActive: boolean }) {
  const icon = INTENT_ICONS[goal.intent_type] || "🎯";
  const allSlots = Object.keys(goal.slots_filled).length + goal.slots_missing.length;
  const filledCount = Object.keys(goal.slots_filled).length;
  const progress = allSlots > 0 ? (filledCount / allSlots) * 100 : 0;

  return (
    <div className={`goal-card ${goal.status} ${isActive ? 'ring-2 ring-blue-500' : ''}`}>
      {/* Header: type + status badge */}
      <div className="goal-card-header">
        <div className="goal-card-type">
          <span className="goal-type-icon">{icon}</span>
          <span className="goal-type-label">{goal.intent_type}</span>
        </div>
        <span className={`status-badge ${goal.status}`}>
          {goal.status === "active" && "● "}
          {goal.status}
        </span>
      </div>

      {/* Slot progress (only for booking goals with slots) */}
      {allSlots > 0 && (
        <div className="slot-progress">
          <div className="slot-progress-bar">
            <div
              className={`slot-progress-fill ${goal.status}`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="slot-list">
            {Object.entries(goal.slots_filled).map(([key, value]) => (
              <span key={key} className="slot-tag filled">
                {key}: {String(value)}
              </span>
            ))}
            {goal.slots_missing.map((slot) => (
              <span key={slot} className="slot-tag missing">
                {slot}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* FAQ goals: simple "answered" indicator when completed */}
      {goal.intent_type === "faq" && goal.status === "completed" && (
        <div className="slot-list" style={{ marginTop: 6 }}>
          <span className="slot-tag filled">✓ answered</span>
        </div>
      )}
    </div>
  );
}
