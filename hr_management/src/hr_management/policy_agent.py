import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import json
import requests
import os
from dotenv import load_dotenv

# Load policy documents (list of paragraphs/sections)
with open("policy_documents.json") as f:
    POLICY_DOCS = json.load(f)

app = FastAPI()
SESSIONS: Dict[str, List[Dict]] = {}

class QARequest(BaseModel):
    session_id: str = None
    questions: List[str]

class QAResponse(BaseModel):
    session_id: str
    answers: List[str]
    memory: List[Dict]
    retrieved_contexts: List[List[str]]

def retrieve_context(question: str, top_k: int = 3) -> List[str]:
    scores = []
    q_words = set(question.lower().split())
    for doc in POLICY_DOCS:
        doc_words = set(doc["text"].lower().split())
        score = len(q_words & doc_words)
        scores.append((score, doc["text"]))
    scores.sort(reverse=True)
    return [text for score, text in scores[:top_k] if score > 0]

def build_prompt(question: str, context: List[str], memory: List[Dict], role: str = "employee") -> str:
    prompt = (
        f"You are a helpful HR assistant answering as a {role}.\n"
        "Use the following policy context to answer the user's question as accurately as possible.\n"
        f"Policy Context:\n{chr(10).join(context) if context else 'N/A'}\n"
        "Conversation History:\n"
        + "\n".join([f"Q: {m['question']} A: {m['answer']}" for m in memory])
        + f"\nUser Question: {question}\n"
        "Answer:"
    )
    return prompt


# Gemini 2.5 Flash API integration
load_dotenv(dotenv_path="../../.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

def gemini_chat(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(GEMINI_API_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "[ERROR] Could not parse Gemini response."

@app.post("/policy_qa", response_model=QAResponse)
async def policy_qa(req: QARequest):
    session_id = req.session_id or str(uuid.uuid4())
    memory = SESSIONS.get(session_id, [])
    answers = []
    retrieved_contexts = []
    for question in req.questions:
        context = retrieve_context(question)
        prompt = build_prompt(question, context, memory)
        answer = gemini_chat(prompt)
        answers.append(answer)
        retrieved_contexts.append(context)
        memory.append({"question": question, "answer": answer})
    SESSIONS[session_id] = memory
    return QAResponse(
        session_id=session_id,
        answers=answers,
        memory=memory,
        retrieved_contexts=retrieved_contexts
    )