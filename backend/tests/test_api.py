"""
Tests for API routes and validation.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_create_session():
    with TestClient(app) as client:
        response = client.post("/api/sessions", json={"metadata": {"platform": "test"}})
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["metadata"] == {"platform": "test"}


def test_get_missing_session():
    with TestClient(app) as client:
        bad_id = str(uuid4())
        response = client.get(f"/api/sessions/{bad_id}")
        assert response.status_code == 404


def test_chat_missing_session():
    with TestClient(app) as client:
        bad_id = str(uuid4())
        response = client.post(
            f"/api/sessions/{bad_id}/chat", json={"message": "hello"}
        )
        assert response.status_code == 404


def test_chat_validation_empty_message():
    with TestClient(app) as client:
        # Create a real session first
        session = client.post("/api/sessions").json()
        session_id = session["id"]

        # Send empty message
        response = client.post(f"/api/sessions/{session_id}/chat", json={"message": ""})
        assert response.status_code == 422
        assert "String should have at least 1 character" in response.text


def test_chat_validation_overlength_message():
    with TestClient(app) as client:
        session = client.post("/api/sessions").json()
        session_id = session["id"]

        # Send huge message
        response = client.post(
            f"/api/sessions/{session_id}/chat", json={"message": "a" * 3000}
        )
        assert response.status_code == 422
        assert "String should have at most 2000 characters" in response.text
