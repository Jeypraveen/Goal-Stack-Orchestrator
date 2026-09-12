"""
Tests for the orchestrator's execute_agent node.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.graph.orchestrator import execute_agent
from app.graph.state import OrchestratorState
from app.models.goal import AgentResponse, Goal, GoalStackState


def create_goal(intent_type="faq", status="active", id=None):
    return Goal(
        id=id or uuid4(),
        session_id=uuid4(),
        intent_type=intent_type,
        status=status,
        slots_filled={},
        slots_missing=[],
        stack_position=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_db():
    with patch("app.graph.orchestrator.get_db") as mock:
        yield mock


@pytest.fixture
def mock_gsm(mock_db):
    with patch("app.graph.orchestrator.GoalStackManager") as mock:
        gsm = AsyncMock()
        mock.return_value = gsm
        yield gsm


@pytest.fixture
def mock_booking_agent():
    with patch("app.graph.orchestrator._get_booking_agent") as mock:
        agent = AsyncMock()
        agent.process.return_value = AgentResponse(
            response="Booking response",
            slots_filled={},
            slots_missing=["origin"],
            is_complete=False,
        )
        mock.return_value = agent
        yield agent


@pytest.fixture
def mock_faq_agent():
    with patch("app.graph.orchestrator._get_faq_agent") as mock:
        agent = AsyncMock()
        agent.process.return_value = AgentResponse(
            response="FAQ response", slots_filled={}, slots_missing=[], is_complete=True
        )
        mock.return_value = agent
        yield agent


@pytest.mark.asyncio
async def test_execute_agent_low_confidence(mock_gsm):
    """Test confidence < 0.5 results in clarification request and no stack mutation."""

    class MockDecision:
        action = "CONTINUE_CURRENT"
        confidence = 0.4
        intent_type = None
        target_goal_id = None

    class MockRouterDecision:
        decisions = [MockDecision()]

    state = {
        "session_id": str(uuid4()),
        "user_message": "wha?",
        "router_decision": MockRouterDecision(),
        "goal_stack": [],
        "active_goal": None,
        "recent_messages": [],
    }

    mock_gsm.get_stack.return_value = GoalStackState(
        session_id=uuid4(), goals=[], active_goal=None
    )

    result = await execute_agent(state)

    assert "not completely sure" in result["agent_response"]
    mock_gsm.push_goal.assert_not_called()
    mock_gsm.resume_goal.assert_not_called()


@pytest.mark.asyncio
async def test_execute_agent_abandon_resumes_below(mock_gsm, mock_booking_agent):
    """Test abandoning a goal resumes the one beneath it."""
    session_id = uuid4()

    class MockDecision:
        action = "ABANDON_GOAL"
        confidence = 0.9
        intent_type = None
        target_goal_id = None

    class MockRouterDecision:
        decisions = [MockDecision()]

    active = create_goal(intent_type="faq")
    resumed = create_goal(intent_type="booking")

    mock_gsm.get_active_goal.return_value = active
    mock_gsm.abandon_goal.return_value = resumed

    # After process finishes, it fetches the stack again
    mock_gsm.get_stack.return_value = GoalStackState(
        session_id=session_id, goals=[resumed], active_goal=resumed
    )

    state = {
        "session_id": str(session_id),
        "user_message": "cancel this faq",
        "router_decision": MockRouterDecision(),
        "goal_stack": [],
        "active_goal": None,
        "recent_messages": [],
    }

    result = await execute_agent(state)

    mock_gsm.abandon_goal.assert_called_once_with(session_id, active.id)
    # The abandoned agent is NOT called. The RESUMED agent (booking) is called.
    mock_booking_agent.process.assert_called_once()
    assert result["active_goal"]["id"] == str(resumed.id)


@pytest.mark.asyncio
async def test_execute_agent_resume_invalid_target_regression(
    mock_gsm, mock_booking_agent
):
    """
    Test bug #1 regression: If RESUME_PAUSED_GOAL is given a bad ID,
    it should gracefully fallback to the active goal.
    """
    session_id = uuid4()
    bad_id = uuid4()

    class MockDecision:
        action = "RESUME_PAUSED_GOAL"
        confidence = 0.9
        intent_type = None
        target_goal_id = str(bad_id)

    class MockRouterDecision:
        decisions = [MockDecision()]

    active = create_goal(intent_type="booking")

    # resume_goal raises ValueError (target invalid)
    mock_gsm.resume_goal.side_effect = ValueError("Target invalid")
    # Fallback fetches current active
    mock_gsm.get_active_goal.return_value = active

    mock_gsm.get_stack.return_value = GoalStackState(
        session_id=session_id, goals=[active], active_goal=active
    )

    state = {
        "session_id": str(session_id),
        "user_message": "resume the other one",
        "router_decision": MockRouterDecision(),
        "goal_stack": [],
        "active_goal": None,
        "recent_messages": [],
    }

    result = await execute_agent(state)

    # It tried to resume the bad ID
    mock_gsm.resume_goal.assert_called_once_with(session_id, bad_id)
    # But it caught the ValueError, fell back to active, and called booking agent
    mock_booking_agent.process.assert_called_once()
    # Active goal stayed active
    assert result["active_goal"]["id"] == str(active.id)
