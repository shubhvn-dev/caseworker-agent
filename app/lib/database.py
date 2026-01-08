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


async def advance_case_step(case_id: str) -> dict | None:
    """Mark the next pending/waiting step as completed and generate follow-up draft."""
    from .agent import generate_followup_draft
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        action_plan = json.loads(row["action_plan"]) if row["action_plan"] else []
        drafts = json.loads(row["drafts"])
        
        # Find and complete the next pending OR waiting step
        completed_step = None
        for step in action_plan:
            if step["status"] in ["pending", "waiting"]:
                step["status"] = "completed"
                completed_step = step
                break
        
        # Generate follow-up draft if a step was completed
        if completed_step:
            case_info = {
                "id": row["id"],
                "subject": row["subject"],
                "issue_area": row["issue_area"],
                "sentiment": row["sentiment"],
                "action_plan": action_plan,
            }
            followup_draft = await generate_followup_draft(case_info, completed_step)
            drafts.append(followup_draft)
        
        # Save updated case
        await db.execute(
            """UPDATE cases 
               SET action_plan = ?, drafts = ?
               WHERE id = ?""",
            (json.dumps(action_plan), json.dumps(drafts), case_id)
        )
        await db.commit()
        
        # Return full case data
        return {
            "id": row["id"],
            "subject": row["subject"],
            "body": row["body"],
            "tags": json.loads(row["tags"]),
            "issue_area": row["issue_area"],
            "sentiment": row["sentiment"],
            "actions": json.loads(row["actions"]),
            "action_plan": action_plan,
            "drafts": drafts,
        }
