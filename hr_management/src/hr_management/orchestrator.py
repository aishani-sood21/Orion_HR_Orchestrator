import uuid
import json
import os
import tempfile
from typing import Dict, Any, List
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import glob

# Import your existing agent functions or classes:
# Assuming you have functions exposed to call these agents programmatically.
from resume_agent import extract_text_from_pdf, call_gemini_extract_fields, call_gemini_score
from onboarding_agent import generate_onboarding_plan
from policy_agent import retrieve_context, build_prompt, gemini_chat

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class OrchestratorResponse(BaseModel):
    candidate_info: CandidateInfo
    onboarding_plan: str
    policy_answers: Dict[str, str]


def save_resume_text(resume_text: str) -> str:
    """Save extracted resume text to read_pdfs folder with auto-incrementing filename."""
    read_pdfs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../read_pdfs"))
    
    # Create directory if it doesn't exist
    os.makedirs(read_pdfs_dir, exist_ok=True)
    
    # Find the next available file number
    existing_files = glob.glob(os.path.join(read_pdfs_dir, "resume_text_*.txt"))
    if existing_files:
        # Extract numbers from filenames and find the max
        numbers = []
        for file in existing_files:
            try:
                num = int(os.path.basename(file).replace("resume_text_", "").replace(".txt", ""))
                numbers.append(num)
            except ValueError:
                continue
        next_num = max(numbers) + 1 if numbers else 1
    else:
        next_num = 1
    
    # Save the file
    filename = f"resume_text_{next_num}.txt"
    filepath = os.path.join(read_pdfs_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(resume_text)
    
    return filename


@app.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate_workflow(
    pdf_file: UploadFile = File(...),
    job_role: str = Form(...),
    policy_questions: str = Form("[]"),
):
    session_id = str(uuid.uuid4())
    memory = {"policy": []}

    temp_path = None
    try:
        # 1. Persist uploaded resume temporarily and process it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await pdf_file.read())
            temp_path = temp_file.name

        resume_text = extract_text_from_pdf(temp_path)
        
        # Save extracted resume text to read_pdfs folder
        saved_filename = save_resume_text(resume_text)
        
        fields = call_gemini_extract_fields(resume_text)
        score = call_gemini_score(fields, job_role)

        cgpa_value = fields.get("CGPA")
        if cgpa_value is None:
            cgpa_value = "N/A"

        candidate_info = CandidateInfo(
            name=fields.get("Name", "N/A"),
            College=fields.get("College", "N/A"),
            Tech_skills=fields.get("Tech Skills", []),
            Soft_skills=fields.get("Soft Skills", []),
            CGPA=str(cgpa_value),
            score=score
        )

        # 2. Generate onboarding plan
        onboarding_plan = generate_onboarding_plan(candidate_info.dict())

        # 3. Policy Q&A
        try:
            parsed_questions = json.loads(policy_questions) if policy_questions else []
            if not isinstance(parsed_questions, list):
                parsed_questions = []
        except json.JSONDecodeError:
            parsed_questions = []

        policy_answers = {}
        session_memory = []
        for question in parsed_questions:
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
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=9000)



