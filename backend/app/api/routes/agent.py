# app/api/routes/agent.py
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document
from app.llm.client import client, MODEL  # Uses your healthy OpenRouter client

router = APIRouter(prefix="/agent", tags=["AI Coding Agent"])

# The structure we expect from the frontend request
class DiagnoseRequest(BaseModel):
    error_log: Optional[str] = None  # User can optionally provide this

# The structured format the AI MUST reply with
class FilePatch(BaseModel):
    file_path: str
    bug_description: str
    original_code_snippet: str
    fixed_code_snippet: str
    full_fixed_file: str

class DiagnosticResponse(BaseModel):
    status: str
    summary: str
    patches: List[FilePatch]

@router.post("/projects/{project_id}/diagnose", response_model=DiagnosticResponse)
def diagnose_and_fix_project(project_id: int, request: DiagnoseRequest, db: Session = Depends(get_db)):
    # 1. Fetch all ingested document codes for this project from your database context
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    if not docs:
        raise HTTPException(status_code=404, detail="No files found for this project. Ingest it first!")

    # 2. Combine the files into a readable context for the AI
    code_context = ""
    for doc in docs:
        # Assuming your Document model has file_path and a way to hold contents or chunks
        code_context += f"\n--- FILE: {doc.file_path} ---\n"
        # Gather text content from the chunks or file_path if stored locally
        # For simplicity, we assume doc has an accessible text structure or content field
        content_snippet = getattr(doc, "content", "Code data stored in vector database chunks.")
        code_context += f"{content_snippet}\n"

    # 3. Determine if we are Auditing or Fixing an explicit error
    if request.error_log and request.error_log.strip():
        # Mode 2: User told us the error
        mode_instruction = (
            f"The user reported the following application error crash log:\n{request.error_log}\n"
            "Your primary mission is to trace this error to the bad file, pinpoint the mistake, and fix it."
        )
    else:
        # Mode 1: AI must find the error by itself
        mode_instruction = (
            "The user has not provided an error log. Your primary mission is to proactively audit this codebase. "
            "Scan the file code context for syntax errors, logical bugs, missing imports, typos (like 'sll' instead of 'all'), "
            "deprecated library setups, or obvious runtime crash points. Generate a proactive fix for the most critical bug you find."
        )

    system_prompt = (
        "You are an elite, autonomous AI Software Engineer and Quality Auditor.\n"
        f"{mode_instruction}\n"
        "You must analyze the code context and return your answer in a strict structured format matching the schema provided."
    )

    user_prompt = f"Here is the project codebase context:\n{code_context}"

    try:
        # 4. Ask OpenRouter for a structured object parsing
        completion = client.beta.chat.completions.parse(
            model=MODEL, # Uses your 'openrouter/free' setting
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=DiagnosticResponse,
            temperature=0.1
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent failed to parse code: {str(e)}")
