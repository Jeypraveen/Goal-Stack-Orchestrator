import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from app.agents.booking import BookingAgent, ExtractedSlots
from app.models.goal import Goal


@pytest.fixture
def mock_goal():
    return Goal(
        id=uuid4(),
        session_id=uuid4(),
        intent_type="booking",
        status="active",
        slots_filled={
            "origin": "NYC",
            "destination": "LHR",
        },
        slots_missing=["date"],
        stack_position=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_api_retry_success(mock_goal):
    """Test that the API successfully retries and recovers after 2 failures."""
    agent = BookingAgent()

    # Mock slot extraction to return the final missing piece
    mock_extractor = AsyncMock()
    mock_extractor.ainvoke.return_value = ExtractedSlots(date="2026-10-15")
    agent._extractor = mock_extractor

    # Mock the response generator so we don't actually hit Gemini
    mock_generate = AsyncMock()
    mock_generate.return_value = "Booking confirmed!"

    # We patch _generate_response directly to capture kwargs
    with patch.object(agent, "_generate_response", mock_generate):
        response = await agent.process(
            user_message="October 15th", goal=mock_goal, simulate_failure_count=2
        )

        mock_generate.assert_called_once()
        kwargs = mock_generate.call_args.kwargs
        # fallback for positional or kwargs
        if "api_failed" in kwargs:
            assert kwargs["api_failed"] is False
        else:
            # It's the 6th argument
            assert mock_generate.call_args.args[5] is False

        assert response.is_complete is True


@pytest.mark.asyncio
async def test_api_retry_exhausted_graceful_degradation(mock_goal):
    """Test that exactly 3 or more failures exhausts retries and degrades gracefully."""
    agent = BookingAgent()

    mock_extractor = AsyncMock()
    mock_extractor.ainvoke.return_value = ExtractedSlots(date="2026-10-15")
    agent._extractor = mock_extractor

    # Let's mock ainvoke directly on the class
    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", new_callable=AsyncMock
    ) as mock_llm:
        response = await agent.process(
            user_message="October 15th",
            goal=mock_goal,
            simulate_failure_count=4,  # More than max retries (3)
        )

        # LLM shouldn't even be called because api_failed returns early
        mock_llm.assert_not_called()

        # Assert graceful degradation message
        assert "airline system is currently busy" in response.response
        assert response.is_complete is True
