import pytest
from app.services.goal_stack import GoalStackManager
from app.services.session import SessionService

pytestmark = pytest.mark.asyncio


async def test_push_goal_makes_it_active(db):
    session_svc = SessionService(db)
    session = await session_svc.create_session()

    gsm = GoalStackManager(db)
    goal = await gsm.push_goal(session.id, "booking")

    assert goal.status == "active"
    assert goal.intent_type == "booking"
    assert goal.session_id == session.id
    assert goal.stack_position == 0


async def test_push_second_goal_pauses_first(db):
    session_svc = SessionService(db)
    session = await session_svc.create_session()

    gsm = GoalStackManager(db)
    goal1 = await gsm.push_goal(session.id, "booking")
    assert goal1.status == "active"

    goal2 = await gsm.push_goal(session.id, "faq")
    assert goal2.status == "active"
    assert goal2.stack_position == 1

    # Check that goal1 was paused
    stack = await gsm.get_stack(session.id)
    assert len(stack.goals) == 2
    assert stack.goals[0].id == goal2.id
    assert stack.goals[0].status == "active"
    assert stack.goals[1].id == goal1.id
    assert stack.goals[1].status == "paused"


async def test_pop_goal_resumes_paused(db):
    session_svc = SessionService(db)
    session = await session_svc.create_session()

    gsm = GoalStackManager(db)
    goal1 = await gsm.push_goal(session.id, "booking")
    goal2 = await gsm.push_goal(session.id, "faq")

    # Pop goal2
    resumed_goal = await gsm.pop_goal(session.id)
    assert resumed_goal is not None
    assert resumed_goal.id == goal1.id
    assert resumed_goal.status == "active"

    stack = await gsm.get_stack(session.id)
    assert stack.goals[0].status == "completed"
    assert stack.goals[0].id == goal2.id
    assert stack.goals[1].status == "active"
    assert stack.goals[1].id == goal1.id
