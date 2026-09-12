"""
LangGraph Orchestrator — the main control flow graph.

This graph processes every incoming user message through:
    1. load_state — Fetch goal stack + recent messages from SQLite
    2. route_message — Classify the message via Router LLM (Groq)
    3. execute_agent — Update goal stack + dispatch to the correct agent
    4. persist_state — Write all changes back to SQLite
    5. format_response — Package response + goal stack for the API

Uses LangGraph's StateGraph for explicit, debuggable control flow
rather than an opaque agent loop.
"""

import logging
from uuid import UUID

from langgraph.graph import StateGraph, END

from app.agents.booking import BookingAgent
from app.agents.faq import FAQAgent
from app.agents.router import MessageRouter
from app.agents.status import StatusAgent
from app.database import get_db
from app.graph.state import OrchestratorState
from app.models.goal import Goal, GoalStackState, AgentResponse
from app.models.message import MessageCreate
from app.services.goal_stack import GoalStackManager
from app.services.session import SessionService

logger = logging.getLogger(__name__)

# =========================================================================
# Singleton agent instances (stateless, safe to share)
# =========================================================================

_router: MessageRouter | None = None
_booking_agent: BookingAgent | None = None
_faq_agent: FAQAgent | None = None
_status_agent: StatusAgent | None = None


def _get_router() -> MessageRouter:
    global _router
    if _router is None:
        _router = MessageRouter()
    return _router


def _get_booking_agent() -> BookingAgent:
    global _booking_agent
    if _booking_agent is None:
        _booking_agent = BookingAgent()
    return _booking_agent


def _get_faq_agent() -> FAQAgent:
    global _faq_agent
    if _faq_agent is None:
        _faq_agent = FAQAgent()
    return _faq_agent


# =========================================================================
# Graph Nodes
# =========================================================================


def _get_status_agent() -> StatusAgent:
    global _status_agent
    if _status_agent is None:
        _status_agent = StatusAgent()
    return _status_agent


async def load_state(state: OrchestratorState) -> dict:
    """
    Node 1: Load current goal stack and recent messages from SQLite.
    """
    db = get_db()
    session_id = UUID(state["session_id"])

    gsm = GoalStackManager(db)
    session_svc = SessionService(db)

    # Fetch goal stack
    goal_stack_state = await gsm.get_stack(session_id)

    # Fetch recent messages for router context
    recent = await session_svc.get_recent_messages(session_id, limit=10)

    return {
        "goal_stack": [g.model_dump(mode="json") for g in goal_stack_state.goals],
        "active_goal": (
            goal_stack_state.active_goal.model_dump(mode="json")
            if goal_stack_state.active_goal
            else None
        ),
        "recent_messages": [{"role": m.role, "content": m.content} for m in recent],
    }


async def route_message(state: OrchestratorState) -> dict:
    """
    Node 2: Classify the user message via the Router LLM (Groq).
    """
    router = _get_router()
    session_id = UUID(state["session_id"])

    # Build goal stack state for the router
    goals = [Goal(**g) for g in state["goal_stack"]]
    goal_stack_state = GoalStackState(
        session_id=session_id,
        goals=goals,
        active_goal=Goal(**state["active_goal"]) if state["active_goal"] else None,
    )

    decision = await router.route(
        user_message=state["user_message"],
        goal_stack=goal_stack_state,
        recent_messages=state["recent_messages"],
    )

    return {"router_decision": decision}


async def execute_agent(state: OrchestratorState) -> dict:
    """
    Node 3: Based on router decision, update goal stack and dispatch to agent.

    This is where the core goal-stack logic lives:
    - NEW_GOAL_INTERRUPT → push new goal, dispatch to new agent
    - CONTINUE_CURRENT → dispatch to current active goal's agent
    - RESUME_PAUSED_GOAL → resume goal, dispatch to resumed agent
    - ABANDON_GOAL → abandon goal, dispatch to next active agent
    """
    db = get_db()
    session_id = UUID(state["session_id"])
    gsm = GoalStackManager(db)
    decision = state["router_decision"]

    combined_responses = []

    # Process each decision sequentially
    for single_decision in decision.decisions:
        active_goal = None

        # --- Check confidence for clarification ---
        if single_decision.confidence < 0.5:
            combined_responses.append(
                "I'm not completely sure I understood that. Could you please rephrase?"
            )
            continue

        # --- Handle stack operations based on router decision ---
        if single_decision.action == "SMALL_TALK":
            combined_responses.append(
                "Got it! Let me know if there's anything else you need."
            )
            # Small talk doesn't affect the goal stack, skip agent dispatch
            continue

        elif single_decision.action == "NEW_GOAL_INTERRUPT":
            # Check if current goal is interruptible
            active_goal = await gsm.get_active_goal(session_id)
            if active_goal and not getattr(active_goal, "interruptible", True):
                combined_responses.append(
                    f"Please complete your current {active_goal.intent_type} before starting something new."
                )
                continue

            intent_type = single_decision.intent_type or "faq"
            goal = await gsm.push_goal(session_id, intent_type)
            active_goal = goal
            logger.info(f"Pushed new {intent_type} goal: {goal.id}")

        elif single_decision.action == "CONTINUE_CURRENT":
            goal = await gsm.get_active_goal(session_id)
            if goal is None:
                # No active goal — treat as a new goal
                intent_type = single_decision.intent_type or "faq"
                goal = await gsm.push_goal(session_id, intent_type)
            active_goal = goal

        elif single_decision.action == "RESUME_PAUSED_GOAL":
            if single_decision.target_goal_id:
                try:
                    goal = await gsm.resume_goal(
                        session_id, UUID(single_decision.target_goal_id)
                    )
                    active_goal = goal
                    logger.info(f"Resumed goal: {goal.id}")
                except ValueError as e:
                    logger.warning(f"Resume failed: {e}. Falling back to active goal.")
                    active_goal = await gsm.get_active_goal(session_id)
            else:
                # No target specified — try to resume the most recent paused goal
                goal_stack = await gsm.get_stack(session_id)
                paused = [g for g in goal_stack.goals if g.status == "paused"]
                if paused:
                    goal = await gsm.resume_goal(session_id, paused[0].id)
                    active_goal = goal
                else:
                    active_goal = await gsm.get_active_goal(session_id)

        elif single_decision.action == "ABANDON_GOAL":
            current = await gsm.get_active_goal(session_id)
            if current:
                resumed = await gsm.abandon_goal(session_id, current.id)
                active_goal = resumed
                logger.info(f"Abandoned goal: {current.id}")
            else:
                active_goal = None

        # --- Dispatch to the appropriate agent ---
        if active_goal is None:
            combined_responses.append(
                "I'm ready to help! You can ask me to book a flight or "
                "ask any questions about Goal-Stack Orchestrator's platform."
            )
            continue

        # Select agent based on intent type
        if active_goal.intent_type == "booking":
            agent = _get_booking_agent()
        elif active_goal.intent_type == "faq":
            agent = _get_faq_agent()
        elif active_goal.intent_type == "status":
            agent = _get_status_agent()
        else:
            raise ValueError(f"Unknown intent type: {active_goal.intent_type}")

        # Run the agent and validate the response
        agent_response = await agent.process(
            user_message=state["user_message"],
            goal=active_goal,
        )
        
        # Enforce type safety
        if not isinstance(agent_response, AgentResponse):
            raise TypeError(f"Agent {agent.__class__.__name__} did not return an AgentResponse object.")
            
        combined_responses.append(agent_response.response)

        # Update goal slots
        if agent_response.slots_filled or agent_response.slots_missing:
            await gsm.update_slots(active_goal.id, agent_response.slots_filled, agent_response.slots_missing)

        # If the goal is complete, pop it (resumes the next paused goal)
        if agent_response.is_complete:
            resumed = await gsm.pop_goal(session_id)
            logger.info(
                f"Goal {active_goal.id} completed. "
                f"Resumed: {resumed.id if resumed else 'none'}"
            )
            if resumed:
                combined_responses.append(
                    f"\n\n↪️ *Resuming your {resumed.intent_type} "
                    f"from where you left off...*"
                )

    # --- End of decisions loop ---

    updated_stack = await gsm.get_stack(session_id)
    return {
        "agent_response": "\n\n".join(str(r) for r in combined_responses if r),
        "goal_stack": [g.model_dump(mode="json") for g in updated_stack.goals],
        "active_goal": (
            updated_stack.active_goal.model_dump(mode="json")
            if updated_stack.active_goal
            else None
        ),
    }


async def persist_state(state: OrchestratorState) -> dict:
    """
    Node 4: Persist the user message and assistant response to the messages table.
    """
    db = get_db()
    session_id = UUID(state["session_id"])
    session_svc = SessionService(db)
    decision = state["router_decision"]

    active_goal_id = None
    if state.get("active_goal"):
        active_goal_id = UUID(state["active_goal"]["id"])

    decision_actions = (
        ",".join(d.action for d in decision.decisions) if decision else None
    )

    # Store user message
    await session_svc.store_message(
        session_id,
        MessageCreate(
            role="user",
            content=state["user_message"],
            goal_id=active_goal_id,
            router_decision=decision_actions,
        ),
    )

    # Store assistant response
    await session_svc.store_message(
        session_id,
        MessageCreate(
            role="assistant",
            content=state["agent_response"],
            goal_id=active_goal_id,
            router_decision=decision_actions,
        ),
    )

    return {}


async def format_response(state: OrchestratorState) -> dict:
    """
    Node 5: Package the final response for the API.
    """
    decision = state["router_decision"]
    active_goal = state.get("active_goal")

    decision_actions = (
        ",".join(d.action for d in decision.decisions) if decision else None
    )

    return {
        "final_response": {
            "response": state["agent_response"],
            "goal_stack": state["goal_stack"],
            "active_goal_id": active_goal["id"] if active_goal else None,
            "router_decision": decision_actions,
        }
    }


# =========================================================================
# Build the Graph
# =========================================================================


def build_orchestrator_graph() -> StateGraph:
    """
    Build and return the orchestrator StateGraph.

    Flow: load_state â†’ route_message â†’ execute_agent â†’ persist_state â†’ format_response
    """
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("load_state", load_state)
    graph.add_node("route_message", route_message)
    graph.add_node("execute_agent", execute_agent)
    graph.add_node("persist_state", persist_state)
    graph.add_node("format_response", format_response)

    # Define edges (linear flow)
    graph.set_entry_point("load_state")
    graph.add_edge("load_state", "route_message")
    graph.add_edge("route_message", "execute_agent")
    graph.add_edge("execute_agent", "persist_state")
    graph.add_edge("persist_state", "format_response")
    graph.add_edge("format_response", END)

    return graph


# Compiled graph instance (compile once, reuse)
orchestrator_graph = build_orchestrator_graph().compile()
