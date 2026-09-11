import pytest
from unittest.mock import AsyncMock, patch
from app.agents.router import MessageRouter, SingleDecision, RouterDecisions

pytestmark = pytest.mark.asyncio


@patch("app.agents.router.ChatGroq")
async def test_router_single_intent(mock_chat_groq):
    """Test that the router correctly extracts a single intent."""
    mock_llm_instance = mock_chat_groq.return_value
    mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(
        return_value=RouterDecisions(
            decisions=[
                SingleDecision(
                    action="NEW_GOAL_INTERRUPT",
                    intent_type="booking",
                    reasoning="User wants to book a flight",
                    confidence=1.0,
                )
            ]
        )
    )

    router = MessageRouter()
    from app.models.goal import GoalStackState
    import uuid

    dummy_session = uuid.uuid4()
    dummy_stack = GoalStackState(session_id=dummy_session, goals=[], active_goal=None)
    decisions = await router.route("I want to book a flight", dummy_stack, [])

    assert len(decisions.decisions) == 1
    assert decisions.decisions[0].action == "NEW_GOAL_INTERRUPT"
    assert decisions.decisions[0].intent_type == "booking"


@patch("app.agents.router.ChatGroq")
async def test_router_multi_intent(mock_chat_groq):
    """Test that the router extracts multiple intents in correct order."""
    mock_llm_instance = mock_chat_groq.return_value
    mock_llm_instance.with_structured_output.return_value.ainvoke = AsyncMock(
        return_value=RouterDecisions(
            decisions=[
                SingleDecision(
                    action="NEW_GOAL_INTERRUPT",
                    intent_type="faq",
                    reasoning="User asked a question",
                    confidence=1.0,
                ),
                SingleDecision(
                    action="NEW_GOAL_INTERRUPT",
                    intent_type="booking",
                    reasoning="User wants to book a flight",
                    confidence=1.0,
                ),
            ]
        )
    )

    router = MessageRouter()
    from app.models.goal import GoalStackState
    import uuid

    dummy_session = uuid.uuid4()
    dummy_stack = GoalStackState(session_id=dummy_session, goals=[], active_goal=None)
    decisions = await router.route(
        "I want to book a flight, but first what is Jps.ai?", dummy_stack, []
    )

    assert len(decisions.decisions) == 2
    assert decisions.decisions[0].intent_type == "faq"
    assert decisions.decisions[1].intent_type == "booking"
