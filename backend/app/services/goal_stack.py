"""
GoalStackManager — the most important service class in the orchestrator.

All goal-stack state transitions go through this class. It enforces the
critical invariant: at most one goal per session has status = 'active'.

Every mutation is committed to the SQLite database to ensure atomicity.
The stack is fully persisted in SQLite — the system survives
a server restart without losing state.
"""

import json
import uuid
from uuid import UUID
import aiosqlite

from app.models.goal import Goal, GoalStackState


class GoalStackManager:
    """
    Manages the goal stack for all sessions.

    The goal stack is the central data structure of the orchestrator.
    It models conversation state as a stack of goals, not a flat chat log.

    Key operations:
        push_goal   — Start a new goal (pauses the current active goal)
        pop_goal    — Complete the top goal (resumes the paused goal below)
        pause_goal  — Explicitly pause a goal
        resume_goal — Resume a specific paused goal (pauses the current active)
        abandon_goal — Abandon a goal (resumes the next paused goal)
    """

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    # =========================================================================
    # Core Stack Operations
    # =========================================================================

    MAX_STACK_DEPTH = 10

    async def push_goal(
        self, session_id: UUID, intent_type: str, interruptible: bool = True
    ) -> Goal:
        """Push a new goal onto the stack.

        Args:
            session_id: The session to push onto.
            intent_type: The type of goal (booking, faq, status).
            interruptible: Whether this goal can be interrupted by a new goal.
        """
        # 0. Enforce stack depth limit
        async with self._conn.execute(
            """
            SELECT COUNT(*) FROM goal_stack
            WHERE session_id = ? AND status IN ('active', 'paused')
            """,
            (str(session_id),),
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] >= self.MAX_STACK_DEPTH:
                raise ValueError(
                    f"Goal stack limit ({self.MAX_STACK_DEPTH}) reached. "
                    f"Please complete or abandon existing goals first."
                )

        # 1. Pause the current active goal (if any)
        await self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'paused', updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ? AND status = 'active'
            """,
            (str(session_id),),
        )

        # 2. Determine the new stack position
        async with self._conn.execute(
            """
            SELECT COALESCE(MAX(stack_position), -1)
            FROM goal_stack
            WHERE session_id = ?
            """,
            (str(session_id),),
        ) as cursor:
            row = await cursor.fetchone()
            max_pos = row[0] if row else -1

        new_position = max_pos + 1
        slots_missing = self._get_initial_slots(intent_type)

        new_id = str(uuid.uuid4())

        # 3. Insert the new active goal
        async with self._conn.execute(
            """
            INSERT INTO goal_stack
                (id, session_id, intent_type, status, slots_filled, slots_missing, stack_position, interruptible)
            VALUES (?, ?, ?, 'active', ?, ?, ?, ?)
            RETURNING *
            """,
            (
                new_id,
                str(session_id),
                intent_type,
                json.dumps({}),
                json.dumps(slots_missing),
                new_position,
                1 if interruptible else 0,
            ),
        ) as cursor:
            row = await cursor.fetchone()

        await self._conn.commit()
        return self._row_to_goal(row)

    async def pop_goal(self, session_id: UUID) -> Goal | None:
        """Complete the top (active) goal and resume the next paused goal below it."""
        # 1. Mark the current active goal as completed
        async with self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'completed',
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ? AND status = 'active'
            RETURNING *
            """,
            (str(session_id),),
        ) as cursor:
            completed = await cursor.fetchone()

        if completed is None:
            await self._conn.commit()
            return None

        # 2. Resume the highest-positioned paused goal
        async with self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM goal_stack
                WHERE session_id = ? AND status = 'paused'
                ORDER BY stack_position DESC
                LIMIT 1
            )
            RETURNING *
            """,
            (str(session_id),),
        ) as cursor:
            resumed = await cursor.fetchone()

        await self._conn.commit()
        return self._row_to_goal(resumed) if resumed else None

    async def pause_goal(self, session_id: UUID, goal_id: UUID) -> Goal:
        """Explicitly pause a specific goal."""
        async with self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'paused', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND session_id = ? AND status = 'active'
            RETURNING *
            """,
            (str(goal_id), str(session_id)),
        ) as cursor:
            row = await cursor.fetchone()

        await self._conn.commit()
        if row is None:
            raise ValueError(
                f"Goal {goal_id} not found or not active in session {session_id}"
            )
        return self._row_to_goal(row)

    async def resume_goal(self, session_id: UUID, goal_id: UUID) -> Goal:
        """Resume a specific paused goal.

        IMPORTANT: Validates the target goal exists and is paused BEFORE
        pausing the current active goal. This prevents orphaning the active
        goal if the target is invalid (e.g., stale ID from the router).
        """
        # 1. Validate: target goal must exist and be paused for this session
        async with self._conn.execute(
            """
            SELECT id FROM goal_stack
            WHERE id = ? AND session_id = ? AND status = 'paused'
            """,
            (str(goal_id), str(session_id)),
        ) as cursor:
            target_row = await cursor.fetchone()

        if target_row is None:
            raise ValueError(
                f"Goal {goal_id} not found or not paused in session {session_id}"
            )

        # 2. Now safe to pause the current active goal (if any)
        await self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'paused', updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ? AND status = 'active'
            """,
            (str(session_id),),
        )

        # 3. Move the target goal to the top of the stack
        async with self._conn.execute(
            """
            SELECT COALESCE(MAX(stack_position), 0)
            FROM goal_stack
            WHERE session_id = ?
            """,
            (str(session_id),),
        ) as cursor:
            row = await cursor.fetchone()
            max_pos = row[0] if row else 0

        async with self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'active',
                stack_position = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND session_id = ?
            RETURNING *
            """,
            (max_pos + 1, str(goal_id), str(session_id)),
        ) as cursor:
            row = await cursor.fetchone()

        await self._conn.commit()
        return self._row_to_goal(row)

    async def abandon_goal(self, session_id: UUID, goal_id: UUID) -> Goal | None:
        """Abandon a goal and resume the next paused goal below it."""
        # 1. Mark the target goal as abandoned
        await self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'abandoned',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND session_id = ?
            """,
            (str(goal_id), str(session_id)),
        )

        # 2. Resume the highest-positioned paused goal
        async with self._conn.execute(
            """
            UPDATE goal_stack
            SET status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM goal_stack
                WHERE session_id = ? AND status = 'paused'
                ORDER BY stack_position DESC
                LIMIT 1
            )
            RETURNING *
            """,
            (str(session_id),),
        ) as cursor:
            resumed = await cursor.fetchone()

        await self._conn.commit()
        return self._row_to_goal(resumed) if resumed else None

    # =========================================================================
    # Slot Management
    # =========================================================================

    async def update_slots(
        self,
        goal_id: UUID,
        slots_filled: dict,
        slots_missing: list[str],
    ) -> Goal:
        """Update the slots on a goal.

        This performs a MERGE on slots_filled, not a replacement.
        It protects against agents accidentally wiping previously gathered slots
        if they fail to merge before calling this method.
        """
        # 1. Fetch current goal state
        async with self._conn.execute(
            """
            SELECT slots_filled FROM goal_stack WHERE id = ?
            """,
            (str(goal_id),),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            raise ValueError(f"Goal {goal_id} not found")

        # 2. Merge existing and new
        current_slots_filled_str = row["slots_filled"]
        current_slots_filled = (
            json.loads(current_slots_filled_str)
            if isinstance(current_slots_filled_str, str)
            else current_slots_filled_str
        )

        merged_slots_filled = dict(current_slots_filled)
        merged_slots_filled.update(slots_filled)

        # 3. Update DB
        async with self._conn.execute(
            """
            UPDATE goal_stack
            SET slots_filled = ?,
                slots_missing = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING *
            """,
            (json.dumps(merged_slots_filled), json.dumps(slots_missing), str(goal_id)),
        ) as cursor:
            row = await cursor.fetchone()

        await self._conn.commit()
        if row is None:
            raise ValueError(f"Goal {goal_id} not found")
        return self._row_to_goal(row)

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_stack(self, session_id: UUID) -> GoalStackState:
        """Get the full goal stack for a session."""
        async with self._conn.execute(
            """
            SELECT * FROM goal_stack
            WHERE session_id = ?
            ORDER BY stack_position DESC
            """,
            (str(session_id),),
        ) as cursor:
            rows = await cursor.fetchall()

        goals = [self._row_to_goal(row) for row in rows]
        active = next((g for g in goals if g.status == "active"), None)

        return GoalStackState(
            session_id=session_id,
            goals=goals,
            active_goal=active,
        )

    async def get_active_goal(self, session_id: UUID) -> Goal | None:
        """Get only the currently active goal for a session."""
        async with self._conn.execute(
            """
            SELECT * FROM goal_stack
            WHERE session_id = ? AND status = 'active'
            """,
            (str(session_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_goal(row) if row else None

    async def get_last_completed_booking(self, session_id: UUID) -> Goal | None:
        """Get the most recently completed booking goal for a session.

        Used by the StatusAgent to look up booking details without raw SQL.
        """
        async with self._conn.execute(
            """
            SELECT * FROM goal_stack
            WHERE session_id = ? AND intent_type = 'booking' AND status = 'completed'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (str(session_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_goal(row) if row else None

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _get_initial_slots(intent_type: str) -> list[str]:
        """Define the initial required slots for each goal type."""
        slot_definitions = {
            "booking": ["origin", "destination", "date"],
            "faq": [],
            "status": [],
        }
        return slot_definitions.get(intent_type, [])

    @staticmethod
    def _row_to_goal(row) -> Goal:
        """Convert an aiosqlite Row to a Goal Pydantic model."""
        row_dict = dict(row)
        slots_filled = row_dict["slots_filled"]
        slots_missing = row_dict["slots_missing"]

        if isinstance(slots_filled, str):
            slots_filled = json.loads(slots_filled)
        if isinstance(slots_missing, str):
            slots_missing = json.loads(slots_missing)

        return Goal(
            id=row_dict["id"],
            session_id=row_dict["session_id"],
            intent_type=row_dict["intent_type"],
            status=row_dict["status"],
            slots_filled=slots_filled,
            slots_missing=slots_missing,
            stack_position=row_dict["stack_position"],
            created_at=row_dict["created_at"],
            updated_at=row_dict["updated_at"],
            completed_at=row_dict.get("completed_at"),
            interruptible=bool(row_dict.get("interruptible", True)),
        )
