import aiosqlite
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "casework.db")


async def init_db():
    """Initialize the database and create tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                subject TEXT,
                body TEXT,
                tags TEXT,
                issue_area TEXT,
                sentiment TEXT,
                actions TEXT,
                action_plan TEXT,
                drafts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_cached_case(case_id: str, subject: str, body: str):
    """Check if case exists with same content."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM cases WHERE id = ? AND subject = ? AND body = ?",
            (case_id, subject, body)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "tags": json.loads(row["tags"]),
                    "issue_area": row["issue_area"],
                    "sentiment": row["sentiment"],
                    "actions": json.loads(row["actions"]),
                    "action_plan": json.loads(row["action_plan"]) if row["action_plan"] else [],
                    "drafts": json.loads(row["drafts"]),
                }
    return None


async def save_case(result: dict, subject: str, body: str):
    """Save case result to database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO cases 
            (id, subject, body, tags, issue_area, sentiment, actions, action_plan, drafts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["id"],
            subject,
            body,
            json.dumps(result["tags"]),
            result["issue_area"],
            result["sentiment"],
            json.dumps(result["actions"]),
            json.dumps(result.get("action_plan", [])),
            json.dumps(result["drafts"]),
        ))
        await db.commit()


async def get_all_cases():
    """Get all saved cases."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cases ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "subject": row["subject"],
                    "body": row["body"],
                    "tags": json.loads(row["tags"]),
                    "issue_area": row["issue_area"],
                    "sentiment": row["sentiment"],
                    "actions": json.loads(row["actions"]),
                    "action_plan": json.loads(row["action_plan"]) if row["action_plan"] else [],
                    "drafts": json.loads(row["drafts"]),
                }
                for row in rows
            ]

async def advance_case_step(case_id: str):
    """Mark current pending step as completed and advance to next."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get current case
        async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
        
        # Parse action plan
        action_plan = json.loads(row["action_plan"]) if row["action_plan"] else []
        
        # Find first pending step and mark as completed
        for step in action_plan:
            if step["status"] == "pending":
                step["status"] = "completed"
                # Set next waiting step to pending
                break
        
        # Set next waiting step to pending
        for step in action_plan:
            if step["status"] == "waiting":
                step["status"] = "pending"
                break
        
        # Update database
        await db.execute(
            "UPDATE cases SET action_plan = ? WHERE id = ?",
            (json.dumps(action_plan), case_id)
        )
        await db.commit()
        
        # Return updated case
        return {
            "id": row["id"],
            "subject": row["subject"],
            "body": row["body"],
            "tags": json.loads(row["tags"]),
            "issue_area": row["issue_area"],
            "sentiment": row["sentiment"],
            "actions": json.loads(row["actions"]),
            "action_plan": action_plan,
            "drafts": json.loads(row["drafts"]),
        }
