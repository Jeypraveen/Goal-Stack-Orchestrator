import pytest

from app.services.session import SessionService
from app.services.goal_stack import GoalStackManager

pytestmark = pytest.mark.asyncio


async def test_full_goal_lifecycle(db):
    """
    Integration test:
    1. Start a booking goal.
    2. Interrupt with an FAQ goal.
    3. Complete the FAQ goal.
    4. Verify the booking goal resumes.
    """
    session_svc = SessionService(db)
    session = await session_svc.create_session()
    gsm = GoalStackManager(db)

    # 1. Start a booking goal
    goal1 = await gsm.push_goal(session.id, "booking")
    active = await gsm.get_active_goal(session.id)
    assert active.id == goal1.id
    assert active.intent_type == "booking"

    # 2. Interrupt with FAQ goal
    goal2 = await gsm.push_goal(session.id, "faq")
    active = await gsm.get_active_goal(session.id)
    assert active.id == goal2.id
    assert active.intent_type == "faq"

    # Ensure booking is paused
    stack_state = await gsm.get_stack(session.id)
    paused_goals = stack_state.goals
    assert len(paused_goals) == 2
    assert paused_goals[1].status == "paused"
    assert paused_goals[1].intent_type == "booking"

    # 3. Complete FAQ goal
    resumed_goal = await gsm.pop_goal(session.id)

    # 4. Verify booking goal resumes
    assert resumed_goal is not None
    assert resumed_goal.id == goal1.id
    assert resumed_goal.intent_type == "booking"

    active = await gsm.get_active_goal(session.id)
    assert active.id == goal1.id
    assert active.status == "active"
