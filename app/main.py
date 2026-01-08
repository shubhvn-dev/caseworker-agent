import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

from .lib.agent import run_agent_for_case, generate_stage_drafts
from .lib.sample_cases import SAMPLE_CASES
from .lib.database import init_db, get_all_cases, advance_case_step


load_dotenv()


IS_PRODUCTION = os.getenv("ENVIRONMENT") == "production"


daily_calls = {}


def check_daily_limit(ip: str) -> bool:
    """Returns True if allowed, False if limit exceeded."""
    if not IS_PRODUCTION:
        return True
    
    from datetime import date
    today = str(date.today())
    
    if ip not in daily_calls or daily_calls[ip]["date"] != today:
        daily_calls[ip] = {"date": today, "count": 0}
    
    if daily_calls[ip]["count"] >= 5:
        return False
    
    daily_calls[ip]["count"] += 1
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"Database initialized. Environment: {'production' if IS_PRODUCTION else 'development'}")
    yield


app = FastAPI(title="Caseworker Agent API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CaseInput(BaseModel):
    id: str
    subject: str
    body: str


@app.get("/")
def root():
    return {"status": "ok", "message": "Caseworker Agent API"}


@app.get("/sample-cases")
def get_sample_cases():
    return {"cases": SAMPLE_CASES}


@app.get("/cases")
async def get_cases():
    cases = await get_all_cases()
    return {"cases": cases}


@app.post("/run-agent")
async def run_agent(request: Request, cases: List[CaseInput]):
    client_ip = request.client.host
    
    if not check_daily_limit(client_ip):
        raise HTTPException(
            status_code=429, 
            detail="Daily limit reached (5 calls/day). Please try again tomorrow."
        )
    
    results = []
    for case in cases:
        result = await run_agent_for_case(case.dict())
        results.append(result)
    return {"results": results}


@app.post("/cases/{case_id}/advance")
async def advance_case(case_id: str):
    result = await advance_case_step(case_id)
    if result:
        return {"success": True, "case": result}
    return {"success": False, "message": "Case not found"}


@app.post("/generate-drafts")
async def generate_drafts(request: Request):
    data = await request.json()
    case_data = data.get("caseData")
    
    if not case_data:
        raise HTTPException(status_code=400, detail="caseData required")
    
    result = await generate_stage_drafts(case_data)
    return result
