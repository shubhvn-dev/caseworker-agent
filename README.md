# Caseworker Agent --- AI-Powered Constituent Service System

A full-stack **AI-powered caseworker assistant** built with Python and
vanilla JavaScript.\
Caseworker Agent combines a **FastAPI backend** with an **OpenAI-powered
classification engine**, providing automated email triage, sentiment
analysis, action plan generation, and draft response creation --- all
inside a clean, responsive web UI.

The application delivers a polished constituent service experience while
demonstrating agentic AI architecture, structured output parsing, rate
limiting, and modern API design.

------------------------------------------------------------------------

## Features

### Email Classification & Triage

-   Automatic **issue area detection** (Housing, Healthcare,
    Immigration, Employment, Benefits)
-   **4-tier hierarchical tagging** (Category → Subcategory → Topic →
    Specific Problem)
-   **Sentiment analysis** (frustrated, concerned, neutral, hopeful)
-   Batch processing of multiple cases

### AI-Generated Action Plans

-   Step-by-step **action timelines** with day estimates
-   Status tracking (pending/completed) per step
-   One-click **Mark Complete** to advance workflow
-   Visual timeline UI with progress indicators

### Draft Communications

-   Auto-generated **constituent reply** emails
-   Auto-generated **internal staff memos**
-   Copy-to-clipboard functionality
-   Professional tone matching issue severity

### Analytics Dashboard

-   **Issue area distribution** with visual bars
-   **Top problems** breakdown
-   **Sentiment analysis** summary
-   Real-time stats as cases are processed

------------------------------------------------------------------------

## Tech Stack

### Frontend (Web Client)

-   **Vanilla JavaScript**
-   **HTML5 + CSS3**
-   Custom UI system:
    -   Gradient backgrounds
    -   Styled buttons and modals
    -   Tab-based navigation
    -   Progress indicators
-   No frameworks --- lightweight and fast

### Backend

-   **Python 3.11+ + FastAPI**
-   RESTful API returning JSON
-   **OpenAI GPT-4o-mini** for AI processing
-   **SQLite** via SQLAlchemy ORM
-   **Pydantic** for request/response validation
-   Rate limiting (10 requests/day for demo)

### Infrastructure

-   Single-command startup
-   SQLite file-based database
-   Environment configuration via `.env`

------------------------------------------------------------------------

## Architecture & Flow

### High-Level Architecture

-   **Web Client**
    -   Manages navigation and application state
    -   Executes API calls asynchronously
    -   Renders results in real-time
    -   Displays analytics dashboard
-   **FastAPI Backend**
    -   Exposes REST endpoints for cases and agent processing
    -   Calls OpenAI API with structured prompts
    -   Parses and validates AI responses
    -   Persists results to SQLite
-   **OpenAI GPT-4o-mini**
    -   Classifies emails into issue areas
    -   Generates hierarchical tags
    -   Creates action plans with timelines
    -   Drafts professional responses

------------------------------------------------------------------------

## AI Agent Pipeline

Caseworker Agent uses a **single-prompt agentic approach** to process
constituent emails.

### Processing Steps

1.  Receive email (subject + body)
2.  Send to GPT-4o-mini with structured prompt
3.  Parse JSON response with classification, tags, action plan, drafts
4.  Validate and store in database
5.  Return results to frontend

### Structured Output

``` json
{
  "issue_area": "Housing",
  "sentiment": "frustrated",
  "tags": {
    "tier1": "Housing",
    "tier2": "Rental Issues",
    "tier3": "Lease Disputes",
    "tier4": "Security Deposit"
  },
  "action_plan": [],
  "drafts": []
}
```

------------------------------------------------------------------------

## Rate Limiting

-   **10 requests per day** (resets at midnight UTC)
-   Clear error messages when limit reached
-   Configurable via `DAILY_LIMIT` constant

------------------------------------------------------------------------

## API Overview

**Base URL:** `http://localhost:8000`

### Cases

-   `GET /cases` --- Retrieve all saved cases\
-   `GET /cases/{case_id}` --- Retrieve single case\
-   `POST /cases/{case_id}/advance` --- Mark next action step complete

### Agent

-   `POST /run-agent` --- Process email(s) through AI pipeline

### Utilities

-   `GET /sample-cases` --- Load sample test cases\
-   `GET /rate-limit-status` --- Check remaining API calls

------------------------------------------------------------------------

## Setup & Installation

### Prerequisites

-   Python 3.11+
-   OpenAI API key
-   Modern web browser

### Backend (FastAPI)

``` bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

``` text
OPENAI_API_KEY=sk-your-openai-api-key-here
```

Start the server:

``` bash
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`

### Frontend (Web Client)

``` bash
cd frontend
python -m http.server 5500
```

Frontend runs at: `http://localhost:5500`

------------------------------------------------------------------------

## Project Structure

``` text
caseworker-agent/
 ├── backend/
 │    ├── main.py
 │    ├── models.py
 │    ├── schemas.py
 │    ├── database.py
 │    ├── requirements.txt
 │    └── .env
 │
 ├── frontend/
 │    ├── index.html
 │    ├── styles.css
 │    └── app.js
 │
 ├── .gitignore
 └── README.md
```

------------------------------------------------------------------------

## Future Improvements

-   Multi-language support
-   Email inbox integration
-   Staff assignment workflows
-   Advanced analytics
-   Report exports (CSV / PDF)

------------------------------------------------------------------------

## Built For

This project was built as a demonstration for **Civic** --- showcasing
AI-powered constituent service automation.

------------------------------------------------------------------------

## Contact

**Shubhan Kadam**\
📧 dev.shubhankadam@gmail.com
