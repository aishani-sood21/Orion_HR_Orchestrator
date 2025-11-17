import os
from crewai import Agent, Task, Crew
from crewai import LLM
from typing import Dict
from pymongo import MongoClient

# Unset conflicting environment variables
# os.environ.pop("GCLOUD_PROJECT", None)
# os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


# --- 1. Load API Key from .env ---
from dotenv import load_dotenv
load_dotenv(dotenv_path="../../.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. LLM Configuration ---
# MODIFIED: Corrected to a valid and existing model name
LLM_MODEL = "gemini-2.5-flash"

print(f"Initializing model: {LLM_MODEL}...")

onboarding_llm = LLM(
    model=f"gemini/{LLM_MODEL}",
    api_key=GEMINI_API_KEY
)

# --- 3. Agent Definition ---
onboarding_planner = Agent(
    role="Onboarding Planner",
    goal="Create detailed and personalized onboarding plans for new employees of varying lengths.",
    backstory=(
        "You are an expert HR specialist who designs structured and engaging"
        " onboarding programs. Your plans are known for being highly effective,"
        " ensuring new hires feel welcomed, informed, and ready to contribute."
    ),
    llm=onboarding_llm,
    verbose=True,
    allow_delegation=False
)

# --- 4. Core Onboarding Function (MODIFIED) ---
def generate_onboarding_plan(candidate: Dict) -> str:
    """
    Generates an onboarding plan with a length based on the candidate's score.
    """
    score = candidate.get('score', 75)

    if score <= 50:
        plan_duration = 7
    elif score <= 80:
        plan_duration = 5
    else: # score > 80
        plan_duration = 3
    
    print(f"Candidate score is {score}. Generating a {plan_duration}-day plan...")

    candidate_info = (
        f"Name: {candidate.get('name', 'N/A')}\n"
        f"College: {candidate.get('College', 'N/A')}\n"
        f"Tech Skills: {', '.join(candidate.get('Tech skills', []))}\n"
        f"Soft Skills: {', '.join(candidate.get('Soft skills', []))}\n"
    )
    job_description = candidate.get('job description', 'No job description provided')

    # The Task's expected_output is now changed to request a table
    onboarding_task = Task(
        description=(
            f"Generate a concise, day-by-day {plan_duration}-day onboarding plan for the following new hire.\n\n"
            f"**Job Role:**\n{job_description}\n\n"
            f"**Candidate's Profile:**\n{candidate_info}"
        ),
        expected_output=(
            # MODIFIED: This now asks for a short, crisp markdown table
            f"A short and crisp onboarding plan presented in a markdown table. "
            f"The table should have three columns: 'Day', 'Key Activities', and 'Goal'. "
            f"Provide one row for each day of the {plan_duration}-day plan."
        ),
        agent=onboarding_planner
    )

    onboarding_crew = Crew(
        agents=[onboarding_planner],
        tasks=[onboarding_task],
        verbose=False
    )
    
    result = onboarding_crew.kickoff()
    return result.raw

# --- 5. Database Processing Function ---
def process_database_candidates(mongo_uri: str, db_name: str, collection_name: str):
    """
    Connects to MongoDB, finds hired candidates without a plan, generates one, and updates them.
    """
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        print("\n✅ Successfully connected to MongoDB.")
        
        query = {"Hired": "Yes", "onboarding_plan": {"$exists": False}}
        candidates_to_process = list(collection.find(query))
        
        if not candidates_to_process:
            print("\nNo new hired candidates found to process.")
            return

        print(f"\nFound {len(candidates_to_process)} hired candidates to process...")
        
        for candidate in candidates_to_process:
            candidate_name = candidate.get("name", "Unknown")
            print("\n" + "="*60)
            print(f"Processing candidate: {candidate_name}")
            
            plan = generate_onboarding_plan(candidate)
            
            update_result = collection.update_one(
                {"_id": candidate["_id"]},
                {"$set": {"onboarding_plan": plan}}
            )
            
            if update_result.modified_count > 0:
                print(f"✅ Successfully generated and saved plan for {candidate_name}.")
            else:
                print(f"⚠️ Plan generated for {candidate_name}, but the database entry was not updated.")
            
    except Exception as e:
        print(f"❌ An error occurred during database processing: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("\nMongoDB connection closed.")

# --- 6. Main Execution Block ---
if __name__ == "__main__":
    MONGO_URI = "mongodb+srv://publicUser:publicPass123@cluster0.qx07p39.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    DB_NAME = "resume_screening"
    COLLECTION_NAME = "candidates"


    process_database_candidates(MONGO_URI, DB_NAME, COLLECTION_NAME)

    print("\n" + "="*60)
    print("Onboarding process complete.")
    print("="*60)