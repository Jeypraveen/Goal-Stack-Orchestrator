import asyncio
import aiosqlite
import httpx
from app.config import settings

async def test_sqlite_crud():
    print("========================================")
    print("Testing SQLite Connection & CRUD")
    print("========================================")
    try:
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        if db_path.startswith("sqlite:///"):
             db_path = db_path.replace("sqlite:///", "")
             
        # Connect to SQLite
        print(f"Connecting to {db_path}...")
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            print("[SUCCESS] Connected to SQLite!")

            # Create a test table
            print("\nCreating temporary test table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)
            print("[SUCCESS] Table created!")

            # Insert data
            print("\nInserting data...")
            await conn.execute("INSERT INTO test_users (name) VALUES (?)", ("Jps.ai Tester",))
            await conn.commit()
            print("[SUCCESS] Data inserted!")

            # Read data
            print("\nReading data...")
            async with conn.execute("SELECT * FROM test_users") as cursor:
                row = await cursor.fetchone()
                print(f"[SUCCESS] Data read from DB: {dict(row) if row else None}")

            # Delete table (cleanup)
            print("\nCleaning up (dropping table)...")
            await conn.execute("DROP TABLE test_users")
            await conn.commit()
            print("[SUCCESS] Table dropped!")

        print("[SUCCESS] SQLite CRUD Test: PASS\n")

    except Exception as e:
        print(f"[ERROR] SQLite CRUD Test FAILED: {e}")

async def test_local_api():
    print("========================================")
    print("Testing Local FastAPI Endpoints")
    print("========================================")
    
    # We assume the server is running on localhost:8000
    base_url = "http://localhost:8000/api"
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Test Health Check
            print("Checking API Health...")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print(f"[SUCCESS] Health Check PASS: {response.json()}")
            else:
                print(f"[ERROR] API is not running. Did you run 'uvicorn app.main:app'?")
                return

            # 2. Create a Session
            print("\nCreating a new chat session...")
            response = await client.post(f"{base_url}/sessions")
            session_data = response.json()
            session_id = session_data["id"]
            print(f"[SUCCESS] Session created! ID: {session_id}")

            # 3. Get Session Goals (Should be empty initially)
            print("\nFetching goals for session...")
            response = await client.get(f"{base_url}/sessions/{session_id}/goals")
            print(f"[SUCCESS] Goals fetched: {response.json()}")

        except httpx.ConnectError:
            print("[ERROR] Connection Error: Ensure your FastAPI server is running on port 8000 in another terminal!")
            print("   Run: uvicorn app.main:app --reload")

async def main():
    # 1. Test Database Operations
    await test_sqlite_crud()
    
    # 2. Test API Operations
    await test_local_api()

if __name__ == "__main__":
    asyncio.run(main())

