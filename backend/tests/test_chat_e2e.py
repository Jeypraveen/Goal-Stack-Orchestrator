import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.agents.router import RouterDecisions, SingleDecision
from app.models.goal import AgentResponse


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_chat_happy_path(client):
    """
    End-to-End happy path test for the /chat endpoint.
    Mocks the underlying agent logic to simulate a user completing a booking.
    """
    # 1. Create session
    response = client.post("/api/sessions")
    assert response.status_code == 201
    session_id = response.json()["id"]

    with patch(
        "app.agents.router.MessageRouter.route", new_callable=AsyncMock
    ) as mock_route, patch(
        "app.agents.booking.BookingAgent.process", new_callable=AsyncMock
    ) as mock_booking:

        # Turn 1: User says "I want to book a flight"
        mock_route.return_value = RouterDecisions(
            decisions=[
                SingleDecision(
                    action="NEW_GOAL_INTERRUPT",
                    intent_type="booking",
                    reasoning="test",
                    confidence=1.0,
                )
            ]
        )
        mock_booking.return_value = AgentResponse(
            response="Where are you flying from?",
            slots_filled={},
            slots_missing=["origin", "destination", "date"],
            is_complete=False,
        )

        chat_res = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "I want to book a flight"},
        )
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert data["response"] == "Where are you flying from?"
        assert len(data["goal_stack"]) == 1
        assert data["goal_stack"][0]["intent_type"] == "booking"

        # Turn 2: User says "From NY to London on 2024-12-01"
        mock_route.return_value = RouterDecisions(
            decisions=[
                SingleDecision(
                    action="CONTINUE_CURRENT", reasoning="test", confidence=1.0
                )
            ]
        )
        mock_booking.return_value = AgentResponse(
            response="Booking confirmed!",
            slots_filled={
                "origin": "NY",
                "destination": "London",
                "date": "2024-12-01",
            },
            slots_missing=[],
            is_complete=True,
        )

        chat_res2 = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "From NY to London on 2024-12-01"},
        )
        assert chat_res2.status_code == 200
        data2 = chat_res2.json()
        assert data2["response"] == "Booking confirmed!"

        # Verify goal was completed and removed from active stack / status updated
        assert len(data2["goal_stack"]) == 1
        assert data2["goal_stack"][0]["status"] == "completed"
