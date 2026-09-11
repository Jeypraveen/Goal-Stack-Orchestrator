-- =============================================
-- Goal-Stack Orchestrator — Initial Schema
-- =============================================
-- This is the HEART of the project: the goal-stack data model.
-- Run this migration against your Supabase Postgres instance.

-- Enable UUID generation (Supabase has this by default, but being explicit)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================
-- 1. Sessions table
-- =============================================
-- Each session represents one user conversation.
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB NOT NULL DEFAULT '{}'
);

-- =============================================
-- 2. Goal Stack table — the central data structure
-- =============================================
-- Each row is a goal on the stack. The stack is per-session.
-- CRITICAL INVARIANT: At most one goal per session has status = 'active'.
CREATE TABLE IF NOT EXISTS goal_stack (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    intent_type     VARCHAR(50) NOT NULL,          -- 'booking', 'faq', etc.
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    slots_filled    JSONB NOT NULL DEFAULT '{}',   -- e.g. {"origin": "NYC", "date": "2026-12-01"}
    slots_missing   JSONB NOT NULL DEFAULT '[]',   -- e.g. ["destination"]
    stack_position  INTEGER NOT NULL,              -- 0 = bottom of stack, higher = top
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,                   -- set when status → completed/abandoned

    -- Enforce: no two goals at the same position in the same session
    UNIQUE (session_id, stack_position)
);

-- Partial unique index: enforce at most one active goal per session
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_goal_per_session
    ON goal_stack (session_id)
    WHERE status = 'active';

-- =============================================
-- 3. Messages table — conversation log
-- =============================================
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    goal_id         UUID REFERENCES goal_stack(id), -- which goal was active when this was sent
    router_decision VARCHAR(30),                    -- CONTINUE_CURRENT, NEW_GOAL_INTERRUPT, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================
-- 4. Indexes for query performance
-- =============================================
CREATE INDEX IF NOT EXISTS idx_goals_session
    ON goal_stack(session_id);

CREATE INDEX IF NOT EXISTS idx_goals_session_status
    ON goal_stack(session_id, status);

CREATE INDEX IF NOT EXISTS idx_goals_session_position
    ON goal_stack(session_id, stack_position DESC);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON messages(session_id);

CREATE INDEX IF NOT EXISTS idx_messages_session_created
    ON messages(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_messages_goal
    ON messages(goal_id);
