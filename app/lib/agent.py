import os
import json
from dotenv import load_dotenv
from google import genai
from .taxonomy import get_taxonomy_prompt_list, get_issue_area
from .database import get_cached_case, save_case


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.0-flash"  # Current model name


async def get_tags(text: str) -> dict:
    """Use Gemini to assign Tier 1–4 tags."""
    taxonomy_list = get_taxonomy_prompt_list()
    
    prompt = f"""You are a casework tagger for a congressional office.

Given a constituent message, pick the single best matching path from this taxonomy:

{taxonomy_list}

Constituent message:
{text}

Respond with JSON only, no markdown:
{{"tier1": "...", "tier2": "...", "tier3": "...", "tier4": "..."}}"""
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    
    response_text = response.text.strip()
    
    # Clean up markdown if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    
    return json.loads(response_text)


# def decide_actions(tags: dict) -> list[str]:
#     """Decide next actions based on tags."""
#     actions = []
#     problem = (tags.get("tier4") or "").lower()
    
#     if "documentation" in problem or "records" in problem:
#         actions.append("REQUEST_DOCS_FROM_CONSTITUENT")
    
#     actions.append("CONTACT_AGENCY")
#     return actions
async def create_action_plan(tags: dict, text: str) -> list[dict]:
    """Use Gemini to create a multi-step action plan."""
    
    prompt = f"""You are a congressional caseworker planning next steps for a constituent case.

Case details:
- Agency: {tags.get('tier1')}
- Subagency: {tags.get('tier2')}
- Program: {tags.get('tier3')}
- Problem: {tags.get('tier4')}

Original message:
{text}

Create a 3-5 step action plan. For each step include:
- action: short action name (e.g., "Request Documents", "Contact Agency", "Follow Up")
- description: one sentence explaining what to do
- status: "pending" for first step, "waiting" for rest
- days_from_now: when to do this (0 for immediate, 7, 14, etc.)

Respond with JSON only, no markdown:
{{"steps": [
  {{"action": "...", "description": "...", "status": "pending", "days_from_now": 0}},
  ...
]}}"""

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    
    response_text = response.text.strip()
    
    # Clean up markdown if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    
    try:
        data = json.loads(response_text)
        return data.get("steps", [])
    except:
        # Fallback if parsing fails
        return [
            {"action": "Contact Agency", "description": "Reach out to the agency for status.", "status": "pending", "days_from_now": 0},
            {"action": "Follow Up", "description": "Follow up if no response.", "status": "waiting", "days_from_now": 14}
        ]



async def draft_email(tags: dict, action: str, original_subject: str) -> dict:
    """Draft an email for the given action."""
    
    if action == "REQUEST_DOCS_FROM_CONSTITUENT":
        prompt = f"""Draft a short, polite email to a constituent asking them to provide 
missing documents for their {tags['tier3']} case regarding {tags['tier4']}.
Keep it under 100 words. Be professional but warm."""
    else:
        prompt = f"""Draft a short, professional email to {tags['tier2']} inquiring about 
the status of a constituent's {tags['tier3']} case regarding {tags['tier4']}.
Keep it under 100 words. Be formal and include a request for status update."""
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    
    return {
        "type": action,
        "subject": f"Re: {original_subject}",
        "body": response.text.strip()
    }


async def run_agent_for_case(msg: dict) -> dict:
    """Run the full agent pipeline for a single case."""
    
    # Check cache first
    cached = await get_cached_case(msg["id"], msg["subject"], msg["body"])
    if cached:
        print(f"Cache hit for case {msg['id']}")
        return cached
    
    print(f"Processing case {msg['id']} with Gemini...")
    
    text = f"Subject: {msg['subject']}\n\n{msg['body']}"
    
    # Step 1: Get tags
    tags = await get_tags(text)
    
    # Step 2: Get issue area
    issue_area = get_issue_area(tags.get("tier1", ""))
    
    # Step 3: Get sentiment
    sentiment = await get_sentiment(text)
    
    # Step 4: Create action plan
    action_plan = await create_action_plan(tags, text)
    
    # Step 5: Get simple actions list (for backwards compatibility)
    actions = [step["action"].upper().replace(" ", "_") for step in action_plan]
    
    # Step 6: Draft emails for first two actions
    drafts = []
    for step in action_plan[:2]:
        draft = await draft_email(tags, step["action"], msg["subject"])
        drafts.append(draft)
    
    result = {
        "id": msg["id"],
        "tags": tags,
        "issue_area": issue_area,
        "sentiment": sentiment,
        "actions": actions,
        "action_plan": action_plan,
        "drafts": drafts
    }
    
    # Save to cache
    await save_case(result, msg["subject"], msg["body"])
    
    return result




async def get_sentiment(text: str) -> str:
    """Use Gemini to analyze sentiment."""
    prompt = f"""Analyze the sentiment of this constituent message.

Message:
{text}

Respond with exactly one word: positive, neutral, or negative"""
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    
    sentiment = response.text.strip().lower()
    
    # Normalize response
    if "positive" in sentiment:
        return "positive"
    elif "negative" in sentiment:
        return "negative"
    else:
        return "neutral"
