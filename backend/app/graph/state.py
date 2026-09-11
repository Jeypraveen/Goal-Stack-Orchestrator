"""
LangGraph state schema for the orchestrator.

Defines the shared state that flows through all nodes in the graph.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.agents.router import RouterDecisions


class OrchestratorState(TypedDict):
    """
    State that flows through the orchestrator graph.

    Each field is populated or updated by different nodes:
    - load_state: session_id, goal_stack, active_goal, messages
    - route_message: router_decision
    - execute_agent: agent_response, goal_stack (updated), active_goal (updated)
    - persist_state: (writes to DB, no new state)
    - format_response: final_response
    """

    # Input
    session_id: str
    user_message: str

    # State loaded from DB
    goal_stack: list[dict]
    active_goal: dict | None
    recent_messages: list[dict]

    # Router output
    router_decision: RouterDecisions | None

    # Agent output
    agent_response: str

    # Final packaged response
    final_response: dict

    # LangGraph message history (for checkpointing)
    messages: Annotated[list, add_messages]
