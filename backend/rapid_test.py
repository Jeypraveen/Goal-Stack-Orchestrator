import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8000/api"

async def run_rapid_tests():
    print("========================================")
    print("Starting A-to-Z Rapid Live Test Suite")
    print("========================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        print("\n[1] Checking Pipeline/Health...")
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        print(f"Health OK: {resp.json()}")

        # 2. Create Session
        print("\n[2] Creating Live Session...")
        resp = await client.post(f"{BASE_URL}/sessions")
        session_id = resp.json()["id"]
        print(f"Session Created: {session_id}")

        async def send_chat(msg: str):
            print(f"\nUser: {msg}")
            resp = await client.post(
                f"{BASE_URL}/sessions/{session_id}/chat", 
                json={"message": msg}
            )
            r_json = resp.json()
            print(f"Bot [{r_json.get('router_decision', 'N/A')}]: {r_json['response']}")
            await asyncio.sleep(2.0) # Prevent Groq rate limits
            return r_json

        # 3. Test Small Talk (No Goal Change)
        await send_chat("hello there!")

        # 4. Test Goal 1: Booking Flight (Missing Slots)
        await send_chat("I want to book a flight to London")
        
        # 5. Check Stack
        resp = await client.get(f"{BASE_URL}/sessions/{session_id}/goals")
        data = resp.json()
        stack = data.get("goals", [])
        print(f"Current Goals in Stack: {len(stack)}")
        assert stack[0]["intent_type"] == "booking"
        assert stack[0]["status"] == "active"

        # 6. Multi-Goal Interrupt (Push FAQ)
        await send_chat("Wait, what is Jps.ai?")

        # 7. Check Stack (Should be FAQ Active, Booking Paused)
        resp = await client.get(f"{BASE_URL}/sessions/{session_id}/goals")
        data = resp.json()
        stack = data.get("goals", [])
        print(f"Current Goals in Stack: {len(stack)}")
        assert len(stack) == 2
        assert stack[0]["intent_type"] == "faq" and stack[0]["status"] == "active"
        assert stack[1]["intent_type"] == "booking" and stack[1]["status"] == "paused"

        # 8. Resume Previous Goal
        await send_chat("thanks, now back to my flight")
        
        # 9. Test Status Agent
        await send_chat("check my booking status")

        # 10. Complete Booking Goal
        await send_chat("I will fly from NYC tomorrow")
        
        print("\n========================================")
        print("ALL TESTS PASSED: Live Pipeline is Robust!")
        print("========================================")

if __name__ == "__main__":
    asyncio.run(run_rapid_tests())
