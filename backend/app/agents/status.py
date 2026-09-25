"""
Status Agent - a deterministic, rule-based agent.

This agent checks the status of bookings without using an LLM.
It proves that the goal-stack architecture supports hybrid
(LLM + deterministic) agents.
"""

import logging

from app.database import get_db
from app.models.goal import Goal, AgentResponse
from app.services.goal_stack import GoalStackManager

logger = logging.getLogger(__name__)


class StatusAgent:
    """
    Deterministic rule-based agent for checking booking status.
    No LLM involved - uses the GoalStackManager service layer.
    """

    async def process(
        self,
        user_message: str,
        goal: Goal,
    ) -> AgentResponse:
        """
        Process a status check request.
        Looks for completed booking goals in the session via the service layer.
        """
        try:
            db = get_db()
            gsm = GoalStackManager(db)

            # Use the service layer instead of raw SQL
            completed_booking = await gsm.get_last_completed_booking(goal.session_id)

            if completed_booking:
                slots = completed_booking.slots_filled
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
            return AgentResponse(
                response=response, slots_filled={}, slots_missing=[], is_complete=False
            )

        # Status goals are single-turn - complete immediately on success
        return AgentResponse(
            response=response, slots_filled={}, slots_missing=[], is_complete=True
        )
