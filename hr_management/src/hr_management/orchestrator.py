import uuid
from typing import Dict, Any, List
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import your existing agent functions or classes:
# Assuming you have functions exposed to call these agents programmatically.
from resume_agent import extract_text_from_pdf, call_gemini_extract_fields, call_gemini_score
from onboarding_agent import generate_onboarding_plan
from policy_agent import retrieve_context, build_prompt, gemini_chat

app = FastAPI()

# Simple centralized memory storage, keyed by session_id
SESSION_MEMORY: Dict[str, Dict[str, Any]] = {}

# Define input/output request models for orchestration API
class CandidateInfo(BaseModel):
    name: str
    College: str
    Tech_skills: List[str]
    Soft_skills: List[str]
    CGPA: str = "N/A"
    score: int

class OrchestratorRequest(BaseModel):
    pdf_path: str
    job_role: str
    policy_questions: List[str] = []

class OrchestratorResponse(BaseModel):
    candidate_info: CandidateInfo
    onboarding_plan: str
    policy_answers: Dict[str, str]


@app.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate_workflow(input_data: OrchestratorRequest):
    session_id = str(uuid.uuid4())
    memory = {"policy": []}

    # 1. Resume screening: extract fields and score candidate
    resume_text = extract_text_from_pdf(input_data.pdf_path)
    fields = call_gemini_extract_fields(resume_text)
    score = call_gemini_score(fields, input_data.job_role)

    candidate_info = CandidateInfo(
        name=fields.get("Name", "N/A"),
        College=fields.get("College", "N/A"),
        Tech_skills=fields.get("Tech Skills", []),
        Soft_skills=fields.get("Soft Skills", []),
        CGPA=fields.get("CGPA", "N/A"),
        score=score
    )

    # 2. Generate onboarding plan
    onboarding_plan = generate_onboarding_plan(candidate_info.dict())

    # 3. Policy Q&A
    policy_answers = {}
    session_memory = []
    for question in input_data.policy_questions:
        context = retrieve_context(question)
        prompt = build_prompt(question, context, session_memory)
        answer = gemini_chat(prompt)
        policy_answers[question] = answer
        session_memory.append({"question": question, "answer": answer})
    memory["policy"] = session_memory
    SESSION_MEMORY[session_id] = memory

    return OrchestratorResponse(
        candidate_info=candidate_info,
        onboarding_plan=onboarding_plan,
        policy_answers=policy_answers
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=9000)



