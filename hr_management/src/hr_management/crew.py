from crewai import Crew, Task
from resume_agent import extract_text_from_pdf, call_gemini_extract_fields, call_gemini_score
from onboarding_agent import generate_onboarding_plan, onboarding_planner
from policy_agent import policy_agent
from policy_qa import retrieve_context, build_prompt, gemini_chat

class Memory:
    def __init__(self):
        self.data = {}

    def add(self, key, value):
        self.data.setdefault(key, []).append(value)

    def get(self, key):
        return self.data.get(key, [])

memory = Memory()

def resume_screening_task(pdf_path, job_role):
    resume_text = extract_text_from_pdf(pdf_path)
    fields = call_gemini_extract_fields(resume_text)
    score = call_gemini_score(fields, job_role)
    memory.add("resume_screening", {"fields": fields, "score": score, "job_role": job_role})
    return fields, score

def onboarding_task(fields, score, job_role):
    candidate = {
        "name": fields.get("Name"),
        "College": fields.get("College"),
        "Tech skills": fields.get("Tech Skills", []),
        "Soft skills": fields.get("Soft Skills", []),
        "score": score,
        "job description": job_role
    }
    plan = generate_onboarding_plan(candidate)
    memory.add("onboarding", {"candidate": candidate, "plan": plan})
    return plan

def policy_qa_task(questions):
    session_memory = memory.get("policy_qa")
    answers = []
    for question in questions:
        context = retrieve_context(question)
        prompt = build_prompt(question, context, session_memory)
        answer = gemini_chat(prompt)
        answers.append(answer)
        memory.add("policy_qa", {"question": question, "answer": answer})
    return answers

# Define Crew tasks
resume_task = Task(
    description="Screen resumes and extract candidate details.",
    expected_output="Extracted fields and score for the candidate.",
    agent=None,  # No explicit Agent object in resume_agent.py
    run=resume_screening_task
)

onboarding_plan_task = Task(
    description="Create onboarding plans for new hires.",
    expected_output="A detailed onboarding plan for the candidate.",
    agent=onboarding_planner,
    run=onboarding_task
)

policy_task = Task(
    description="Answer HR policy questions for employees.",
    expected_output="Answers to all provided HR policy questions.",
    agent=None,  # No explicit Agent object in policy_agent.py
    run=policy_qa_task
)

hr_crew = Crew(
    name="HR Automation Crew",
    tasks=[resume_task, onboarding_plan_task, policy_task]
)