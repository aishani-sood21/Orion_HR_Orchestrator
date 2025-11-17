from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
import uvicorn
import os
import requests
import json
import pdfplumber
import pytesseract
from PIL import Image
import re
import google.generativeai as genai
import ast
from pymongo import MongoClient
import urllib.parse
from dotenv import load_dotenv

app = FastAPI()

HTML_FORM = """
<html>
    <body>
        <h2>Upload Resume PDF</h2>
        <form action="/upload_resume/" enctype="multipart/form-data" method="post">
            <input name="pdf_file" type="file" accept=".pdf"/>
            <input type="submit"/>
        </form>
    </body>
</html>
"""

JOB_ROLE_FORM = """
<html>
    <body>
        <h2>Enter Desired Job Role</h2>
        <form action="/analyze_resume/" method="post">
            <input name="job_role" type="text" placeholder="Job Role"/>
            <input type="submit"/>
        </form>
    </body>
</html>
"""

SELECT_N_FORM = """
<html>
    <body>
        <h2>How many candidates do you want to hire?</h2>
        <form action="/mark_hired/" method="post">
            <input name="n_hire" type="number" min="1" placeholder="Number to hire"/>
            <input type="submit"/>
        </form>
    </body>
</html>
"""

load_dotenv(dotenv_path="../../.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    genai.configure(api_key=GEMINI_API_KEY)
else:
    raise RuntimeError("GEMINI_API_KEY not found in environment. Please check your .env file.")
READ_PDFS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../read_pdfs"))

class ResumeConfig:
    MONGODB_USERNAME = "publicUser"
    MONGODB_PASSWORD = "publicPass123"
    MONGODB_CLUSTER = "cluster0.qx07p39.mongodb.net"
    DATABASE_NAME = "resume_screening"
    ENCODED_PASSWORD = urllib.parse.quote_plus(MONGODB_PASSWORD)
    MONGODB_URL = (
        f"mongodb+srv://{MONGODB_USERNAME}:{ENCODED_PASSWORD}"
        f"@{MONGODB_CLUSTER}/"
        f"?retryWrites=true&w=majority&appName=Cluster0"
    )
    CANDIDATES_COLLECTION = "candidates"

@app.get("/", response_class=HTMLResponse)
async def main():
    return HTML_FORM

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            img = page.to_image(resolution=200).original.convert("L")
            img = img.point(lambda x: 0 if x < 180 else 255, '1')
            ocr_text = pytesseract.image_to_string(img)
            combined = page_text + "\n" + ocr_text
            text += combined
    return text

@app.post("/upload_resume/", response_class=HTMLResponse)
async def upload_resume(pdf_file: UploadFile = File(...)):
    # Save PDF and extract text
    pdf_path = f"temp_{pdf_file.filename}"
    with open(pdf_path, "wb") as f:
        f.write(await pdf_file.read())
    resume_text = extract_text_from_pdf(pdf_path)
    os.remove(pdf_path)

    # Store extracted text in numbered .txt file
    os.makedirs(READ_PDFS_PATH, exist_ok=True)
    existing_files = [f for f in os.listdir(READ_PDFS_PATH) if f.startswith("resume_text_") and f.endswith(".txt")]
    next_num = len(existing_files) + 1
    output_path = os.path.join(READ_PDFS_PATH, f"resume_text_{next_num}.txt")
    with open(output_path, "w", encoding="utf-8") as f2:
        f2.write(resume_text)

    # After upload, ask for job role
    html = JOB_ROLE_FORM
    return HTMLResponse(content=html)

def call_gemini_extract_fields(resume_text):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = (
        "Extract the following fields from the resume text. "
        "Return a JSON object with keys: Name, College, CGPA, Tech Skills, Soft Skills. "
        "Resume text: " + resume_text
    )
    response = model.generate_content(prompt)
    cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
    try:
        fields = json.loads(cleaned)
    except Exception:
        try:
            fields = ast.literal_eval(cleaned)
        except Exception:
            print("Failed to parse fields from Gemini response.")
            fields = {}
    return fields

def call_gemini_score(fields, job_role):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = (
        f"Score the following candidate out of 100 for the job role '{job_role}'.\n"
        f"Details: {fields}\n"
        "Give only the score as a number."
    )
    response = model.generate_content(prompt)
    score_text = response.text.strip()
    score_match = re.search(r"\d+", score_text)
    return int(score_match.group()) if score_match else 0

def store_candidate_in_mongo(candidate_data):
    try:
        client = MongoClient(ResumeConfig.MONGODB_URL)
        db = client[ResumeConfig.DATABASE_NAME]
        db[ResumeConfig.CANDIDATES_COLLECTION].insert_one(candidate_data)
    except Exception as e:
        print(f"MongoDB insert error: {e}")

@app.post("/analyze_resume/", response_class=HTMLResponse)
async def analyze_resume(job_role: str = Form(...)):
    # Find the latest resume_text_N.txt file
    resume_files = [f for f in os.listdir(READ_PDFS_PATH) if f.startswith("resume_text_") and f.endswith(".txt")]
    if not resume_files:
        return HTMLResponse(content="<h2>No resume found. Please upload first.</h2>")
    latest_file = sorted(resume_files)[-1]
    resume_path = os.path.join(READ_PDFS_PATH, latest_file)
    with open(resume_path, "r", encoding="utf-8") as f:
        resume_text = f.read()

    # Extract fields using Gemini
    fields = call_gemini_extract_fields(resume_text)
    score = call_gemini_score(fields, job_role)

    # Store in MongoDB Atlas using ResumeConfig
    candidate_data = {
        "Name": fields.get('Name', 'N/A'),
        "College": fields.get('College', 'N/A'),
        "CGPA": fields.get('CGPA', 'N/A'),
        "Tech Skills": fields.get('Tech Skills', 'N/A'),
        "Soft Skills": fields.get('Soft Skills', 'N/A'),
        "Score": score,
        "Job Role": job_role,
        "Source File": latest_file
    }
    store_candidate_in_mongo(candidate_data)

    # Display results on UI with a button to go to select_hired
    html = f"""
    <html>
        <body>
            <h2>Resume Analysis for Job Role: {job_role}</h2>
            <ul>
                <li><strong>Name:</strong> {fields.get('Name', 'N/A')}</li>
                <li><strong>College:</strong> {fields.get('College', 'N/A')}</li>
                <li><strong>CGPA:</strong> {fields.get('CGPA', 'N/A')}</li>
                <li><strong>Tech Skills:</strong> {fields.get('Tech Skills', 'N/A')}</li>
                <li><strong>Soft Skills:</strong> {fields.get('Soft Skills', 'N/A')}</li>
                <li><strong>Score (out of 100):</strong> {score}</li>
            </ul>
            <form action="/select_hired/" method="get">
                <button type="submit">Go to Hire Candidates</button>
            </form>
            <a href="/">Upload another resume</a>
        </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/select_hired/", response_class=HTMLResponse)
async def select_hired():
    return SELECT_N_FORM

@app.post("/mark_hired/", response_class=HTMLResponse)
async def mark_hired(n_hire: int = Form(...)):
    try:
        client = MongoClient(ResumeConfig.MONGODB_URL)
        db = client[ResumeConfig.DATABASE_NAME]
        collection = db[ResumeConfig.CANDIDATES_COLLECTION]
        # Set "Hired" to "No" for all candidates if not already set
        collection.update_many({}, {"$set": {"Hired": "No"}})
        # Find top n_hire candidates by score
        top_candidates = list(collection.find().sort("Score", -1).limit(n_hire))
        # Mark them as hired
        for candidate in top_candidates:
            collection.update_one({"_id": candidate["_id"]}, {"$set": {"Hired": "Yes"}})
        html = "<html><body><h2>Top candidates marked as Hired!</h2><ul>"
        for candidate in top_candidates:
            html += f"<li>{candidate.get('Name', 'N/A')} (Score: {candidate.get('Score', 'N/A')})</li>"
        html += "</ul><a href='/'>Upload another resume</a></body></html>"
        return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"<h2>Error: {e}</h2>")

# Ensure read_pdfs folder exists at startup
os.makedirs(READ_PDFS_PATH, exist_ok=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)