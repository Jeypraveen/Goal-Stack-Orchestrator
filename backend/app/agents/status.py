"""
Status Agent — a deterministic, rule-based agent.

This agent checks the status of bookings without using an LLM.
It proves that the goal-stack architecture supports hybrid
(LLM + deterministic) agents.
"""

import logging
from app.models.goal import Goal, AgentResponse
from app.database import get_db

logger = logging.getLogger(__name__)


class StatusAgent:
    """
    Deterministic rule-based agent for checking booking status.
    No LLM involved.
    """

    async def process(
        self,
        user_message: str,
        goal: Goal,
    ) -> AgentResponse:
        """
        Process a status check request.
        For demo purposes, we'll just mock a successful status check
        or look for completed booking goals in the session.
        """
        try:
            db = get_db()

            # Find any completed booking goals for this session
            async with db.execute(
                """
                SELECT slots_filled FROM goal_stack 
                WHERE session_id = ? AND intent_type = 'booking' AND status = 'completed'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (str(goal.session_id),),
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                import json

                slots = json.loads(row["slots_filled"])
                origin = slots.get("origin", "Unknown")
                dest = slots.get("destination", "Unknown")
                date = slots.get("date", "Unknown")

                response = (
                    f"I found a recent booking for you! You are confirmed "
                    f"to fly from {origin} to {dest} on {date}. Your flight "
                    f"is on schedule."
                )
            else:
                response = (
                    "I couldn't find any completed bookings for this session. "
                    "If you'd like to book a flight, just let me know!"
                )

        except Exception as e:
            logger.error(f"Status agent failed: {e}")
            response = "I encountered an error while checking your booking status."

        # Status checks are single-turn
        return AgentResponse(
            response=response,
            slots_filled={},
            slots_missing=[],
            is_complete=True,
        )
