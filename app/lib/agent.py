import os
import json
from dotenv import load_dotenv
from google import genai
from .taxonomy import get_taxonomy_prompt_list, get_issue_area
from .database import get_cached_case, save_case


load_dotenv()


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.0-flash"


# Letter types configuration
LETTER_TYPES = {
    "acknowledgment": {
        "recipient": "Constituent",
        "prompt": "Write a brief acknowledgment letter to the constituent confirming receipt of their case request."
    },
    "agency_inquiry": {
        "recipient": "Agency",
        "prompt": "Write a formal inquiry letter to the relevant government agency requesting status update or action on this case."
    },
    "followup": {
        "recipient": "Constituent",
        "prompt": "Write a follow-up letter to the constituent providing an update on their case status."
    },
    "escalation": {
        "recipient": "Agency Supervisor",
        "prompt": "Write an escalation letter to a senior agency official requesting expedited review of this case."
    },
    "resolution": {
        "recipient": "Constituent",
        "prompt": "Write a resolution letter informing the constituent their case has been resolved."
    }
}

# Map stages to appropriate letter types
STAGE_LETTERS = {
    1: ["acknowledgment"],
    2: ["agency_inquiry", "followup"],
    3: ["followup", "escalation"],
    4: ["escalation", "agency_inquiry"],
    5: ["resolution", "followup"]
}


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
    
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    
    return json.loads(response_text)


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
    
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    
    try:
        data = json.loads(response_text)
        return data.get("steps", [])
    except:
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
    
    if "positive" in sentiment:
        return "positive"
    elif "negative" in sentiment:
        return "negative"
    else:
        return "neutral"


async def run_agent_for_case(msg: dict) -> dict:
    """Run the full agent pipeline for a single case."""
    
    cached = await get_cached_case(msg["id"], msg["subject"], msg["body"])
    if cached:
        print(f"Cache hit for case {msg['id']}")
        return cached
    
    print(f"Processing case {msg['id']} with Gemini...")
    
    text = f"Subject: {msg['subject']}\n\n{msg['body']}"
    
    tags = await get_tags(text)
    issue_area = get_issue_area(tags.get("tier1", ""))
    sentiment = await get_sentiment(text)
    action_plan = await create_action_plan(tags, text)
    actions = [step["action"].upper().replace(" ", "_") for step in action_plan]
    
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
    
    await save_case(result, msg["subject"], msg["body"])
    
    return result


async def generate_followup_draft(case_data: dict, completed_step: dict) -> dict:
    """Generate a follow-up draft after completing an action step."""
    
    prompt = f"""You are a caseworker assistant. A step has been completed on a constituent case.

CASE INFORMATION:
- Case ID: {case_data['id']}
- Issue Area: {case_data['issue_area']}
- Sentiment: {case_data['sentiment']}
- Original Subject: {case_data.get('subject', 'N/A')}

COMPLETED STEP:
- Action: {completed_step['action']}
- Description: {completed_step['description']}

CURRENT ACTION PLAN STATUS:
{json.dumps(case_data['action_plan'], indent=2)}

Generate a follow-up email to the constituent updating them on progress.

Respond in this exact JSON format:
{{
    "type": "Follow-up Update",
    "subject": "Update on Your Case #{case_data['id']}",
    "body": "Dear Constituent,\\n\\n[Professional update about the completed action and next steps]\\n\\nSincerely,\\nConstituent Services"
}}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt]
        )
        
        result = response.text.strip()
        
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
    
    except Exception as e:
        print(f"Error generating follow-up: {e}")
        return {
            "type": "Follow-up Update",
            "subject": f"Update on Your Case #{case_data['id']}",
            "body": f"Dear Constituent,\n\nWe wanted to update you that we have completed the following action on your case:\n\n• {completed_step['action']}\n\nWe will continue working on your case and provide further updates.\n\nSincerely,\nConstituent Services"
        }


async def generate_stage_drafts(case_data: dict) -> dict:
    """Generate drafts based on current stage."""
    
    completed_steps = sum(1 for s in case_data.get("action_plan", []) if s["status"] == "completed")
    current_stage = min(completed_steps + 1, 5)
    
    letter_types_for_stage = STAGE_LETTERS.get(current_stage, ["followup"])
    
    drafts = []
    
    for letter_type in letter_types_for_stage:
        config = LETTER_TYPES[letter_type]
        
        prompt = f"""{config['prompt']}

Case Details:
- Case ID: {case_data.get('id', 'N/A')}
- Issue Area: {case_data.get('issue_area', 'N/A')}
- Agency: {case_data.get('tags', {}).get('tier1', 'Relevant agency')}
- Problem: {case_data.get('tags', {}).get('tier4', 'N/A')}
- Current Stage: Step {current_stage} of {len(case_data.get('action_plan', []))}

Keep the letter professional, concise (under 200 words), and appropriate for a congressional office.

Respond with the letter text only, no JSON or markdown."""

        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )
            
            drafts.append({
                "type": letter_type,
                "recipient": config["recipient"],
                "content": response.text.strip()
            })
        except Exception as e:
            print(f"Error generating {letter_type}: {e}")
    
    return {
        "drafts": drafts,
        "current_stage": current_stage
    }
