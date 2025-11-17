
[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/6wbiKQtd)

# HR Automation Sequential Orchestrator

##  Overview

This orchestrator provides a **unified API endpoint** that processes candidates through a complete HR workflow in one sequential operation:

1. **Resume Screening** → Extract and score candidate information
2. **Onboarding Plan Generation** → Create personalized onboarding schedule
3. **Policy Q&A** → Answer candidate's policy questions

All three agents work together seamlessly through a single API call.

---

##  Architecture

```
┌─────────────────────────────────────────────────┐
│           Orchestrator API (Port 9000)          │
│              /orchestrate endpoint               │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Resume    │ │ Onboarding  │ │  Policy Q&A │
│   Screening │ │    Agent    │ │    Agent    │
│    Agent    │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

##  Project Structure

```
BUILD2BREAK25-ORION/
├── .github/
├── hr_management/
│   ├── policy_service/
│   ├── read_pdfs/
│   └── src/
│       └── hr_management/
│           ├── __pycache__/
│           ├── .env
│           ├── crew.py
│           ├── main.py
│           ├── onboarding_agent.py
│           ├── orchestrator.py              ← Port 9000 (Sequential API)
│           ├── policy_agent.py
│           ├── policy_documents.json
│           ├── policy_qa.py
│           ├── resume_agent.py
│           └── .env
└── README.md
```

---

##  Prerequisites

### Required Software
- Python 3.8+
- MongoDB Atlas account (for candidate storage)
- Gemini API keys

### Required Python Packages

Create `requirements.txt`:

```txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pymongo==4.6.0
requests==2.31.0
crewai==0.1.0
google-generativeai==0.3.1
pdfplumber==0.10.3
pytesseract==0.3.10
Pillow==10.1.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

##  Configuration

### 1. API Keys Setup

Update the following files with your Gemini API keys:

**`resume_agent.py`:**
```python
GEMINI_API_KEY = "YOUR_RESUME_API_KEY"
```

**`onboarding_agent.py`:**
```python
GEMINI_API_KEY = "YOUR_ONBOARDING_API_KEY"
```

**`policy_agent.py`:**
```python
GEMINI_API_KEY = "YOUR_POLICY_API_KEY"
```

### 2. Create Policy Documents

Create `policy_service/policy_documents.json`:

```json
[
  {
    "id": 1,
    "text": "Employees are entitled to 20 days of paid vacation per year. Vacation requests must be submitted at least 2 weeks in advance."
  },
  {
    "id": 2,
    "text": "Remote work policy allows employees to work from home up to 3 days per week with manager approval."
  },
  {
    "id": 3,
    "text": "Health insurance coverage begins on the first day of employment and covers medical, dental, and vision."
  },
  {
    "id": 4,
    "text": "Professional development budget of $2000 per year is available for courses, certifications, and conferences."
  },
  {
    "id": 5,
    "text": "Sick leave policy provides 10 days per year with no doctor's note required for absences under 3 consecutive days."
  }
]
```

### 3. MongoDB Configuration

Ensure MongoDB connection strings are configured in `resume_agent.py` and `onboarding_agent.py`.

**Default (demo) credentials:**
```python
MONGO_URI = "mongodb+srv://publicUser:publicPass123@cluster0.qx07p39.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "resume_screening"
COLLECTION_NAME = "candidates"
```

---

##  Running the Orchestrator

### Start the Service

```bash
uvicorn orchestrator:app --host 0.0.0.0 --port 9000 --reload
```

**Parameters:**
- `--host 0.0.0.0`: Makes the service accessible from any IP
- `--port 9000`: Runs on port 9000
- `--reload`: Auto-reloads on code changes (development only)

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:9000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Access the API

- **Interactive Docs:** http://localhost:9000/docs
- **Alternative Docs:** http://localhost:9000/redoc
- **API Endpoint:** http://localhost:9000/orchestrate

---

##  API Usage

### Endpoint: `/orchestrate`

**Method:** POST

**Request Body:**

```json
{
  "pdf_path": "/path/to/resume.pdf",
  "job_role": "Software Engineer",
  "policy_questions": [
    "How many vacation days do I get?",
    "What is the remote work policy?",
    "Tell me about health insurance"
  ]
}
```

**Parameters:**
- `pdf_path` (required): Absolute or relative path to the PDF resume
- `job_role` (required): Target job role for scoring
- `policy_questions` (optional): List of policy-related questions

**Response:**

```json
{
  "candidate_info": {
    "name": "John Doe",
    "College": "MIT",
    "Tech_skills": ["Python", "Java", "React"],
    "Soft_skills": ["Leadership", "Communication"],
    "CGPA": "8.5",
    "score": 85
  },
  "onboarding_plan": "| Day | Key Activities | Goal |\n|-----|----------------|------|\n| 1 | Orientation | Welcome |\n| 2 | Team intro | Integration |\n| 3 | Project setup | Contribution |",
  "policy_answers": {
    "How many vacation days do I get?": "Employees are entitled to 20 days of paid vacation per year.",
    "What is the remote work policy?": "Employees can work from home up to 3 days per week with manager approval.",
    "Tell me about health insurance": "Health insurance coverage begins on the first day and covers medical, dental, and vision."
  }
}
```

---

##  Usage Examples

### Example 1: Using cURL

```bash
curl -X POST "http://localhost:9000/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "./resumes/john_doe.pdf",
    "job_role": "Software Engineer",
    "policy_questions": [
      "How many vacation days do I get?",
      "What is the remote work policy?"
    ]
  }'
```

### Example 2: Using Python Requests

```python
import requests
import json

url = "http://localhost:9000/orchestrate"

payload = {
    "pdf_path": "./resumes/john_doe.pdf",
    "job_role": "Software Engineer",
    "policy_questions": [
        "How many vacation days do I get?",
        "What is the remote work policy?"
    ]
}

response = requests.post(url, json=payload)
result = response.json()

print("Candidate:", result["candidate_info"]["name"])
print("Score:", result["candidate_info"]["score"])
print("\nOnboarding Plan:")
print(result["onboarding_plan"])
print("\nPolicy Answers:")
for question, answer in result["policy_answers"].items():
    print(f"Q: {question}")
    print(f"A: {answer}\n")
```

### Example 3: Using JavaScript (Fetch API)

```javascript
const orchestrate = async () => {
  const response = await fetch('http://localhost:9000/orchestrate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      pdf_path: './resumes/john_doe.pdf',
      job_role: 'Software Engineer',
      policy_questions: [
        'How many vacation days do I get?',
        'What is the remote work policy?'
      ]
    })
  });
  
  const result = await response.json();
  console.log('Candidate Info:', result.candidate_info);
  console.log('Onboarding Plan:', result.onboarding_plan);
  console.log('Policy Answers:', result.policy_answers);
};

orchestrate();
```

### Example 4: Testing in API Docs

1. Navigate to http://localhost:9000/docs
2. Click on **POST /orchestrate**
3. Click **"Try it out"**
4. Fill in the request body:
   ```json
   {
     "pdf_path": "./test_resume.pdf",
     "job_role": "Data Scientist",
     "policy_questions": ["What is the sick leave policy?"]
   }
   ```
5. Click **"Execute"**
6. View the response below

---

##  Workflow Details

### Step 1: Resume Screening
- Extracts text from PDF using `pdfplumber` and OCR
- Sends text to Gemini API for field extraction
- Scores candidate based on job role match

### Step 2: Onboarding Plan Generation
- Takes candidate score and creates personalized plan
- Score ≤50: 7-day plan
- Score 51-80: 5-day plan
- Score >80: 3-day plan
- Returns markdown table format

### Step 3: Policy Q&A
- Retrieves relevant policy documents
- Uses conversation memory for context
- Generates answers using Gemini API

---

##  Session Memory

The orchestrator maintains session-based memory:

```python
SESSION_MEMORY[session_id] = {
    "policy": [
        {"question": "...", "answer": "..."},
        {"question": "...", "answer": "..."}
    ]
}
```

Each API call generates a unique `session_id` for tracking.

---

##  Troubleshooting

### Issue: "Module not found"

**Solution:**
```bash
# Ensure all agent files are in the same directory
ls -la
# Should show: orchestrator.py, resume_agent.py, onboarding_agent.py, policy_agent.py

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "File not found: policy_documents.json"

**Solution:**
```bash
# Create the policy_service directory
mkdir -p policy_service

# Create the JSON file with policy data
# (See Configuration section above)
```

### Issue: "Connection to MongoDB failed"

**Solution:**
1. Check internet connection
2. Verify MongoDB credentials in agent files
3. Whitelist your IP in MongoDB Atlas
4. Test connection:
   ```bash
   mongosh "mongodb+srv://publicUser:publicPass123@cluster0.qx07p39.mongodb.net/resume_screening"
   ```

### Issue: "PDF extraction failed"

**Solution:**
```bash
# Ensure Tesseract is installed
which tesseract  # On Linux/Mac
where tesseract  # On Windows

# Install if missing:
# Ubuntu: sudo apt-get install tesseract-ocr
# Mac: brew install tesseract
# Windows: Download from GitHub

# Check PDF path is correct
ls -la /path/to/resume.pdf
```

### Issue: "Gemini API error"

**Solution:**
1. Verify API keys are correct
2. Check API quota/limits
3. Test API key:
   ```bash
   curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
   ```

### Issue: "Port 9000 already in use"

**Solution:**
```bash
# Find process using port 9000
lsof -ti:9000  # Linux/Mac
netstat -ano | findstr :9000  # Windows

# Kill the process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Or use a different port
uvicorn orchestrator:app --port 9001
```

---

##  Performance Considerations

### Processing Time
- **Resume extraction:** 2-5 seconds
- **Gemini API calls:** 1-3 seconds each
- **Total per candidate:** 10-20 seconds

### Optimization Tips
1. **Use async operations** for parallel API calls
2. **Cache policy documents** in memory
3. **Implement request queuing** for high load
4. **Add connection pooling** for MongoDB

---

##  Security Best Practices

1. **Never commit API keys** to version control
   ```bash
   # Add to .gitignore
   echo "*.env" >> .gitignore
   echo "*_config.py" >> .gitignore
   ```

2. **Use environment variables**
   ```python
   import os
   GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
   ```

3. **Restrict file access**
   ```python
   # Validate PDF paths
   import os
   if not os.path.exists(pdf_path):
       raise HTTPException(status_code=400, detail="File not found")
   ```

4. **Add authentication**
   ```python
   from fastapi.security import HTTPBearer
   security = HTTPBearer()
   ```

---

##  Testing

### Manual Testing

```bash
# Start the orchestrator
uvicorn orchestrator:app --port 9000

# In another terminal, test the endpoint
curl -X POST "http://localhost:9000/orchestrate" \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Automated Testing

Create `test_orchestrator.py`:

```python
import requests
import pytest

BASE_URL = "http://localhost:9000"

def test_orchestrate_endpoint():
    payload = {
        "pdf_path": "./test_resume.pdf",
        "job_role": "Software Engineer",
        "policy_questions": ["What is the vacation policy?"]
    }
    
    response = requests.post(f"{BASE_URL}/orchestrate", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "candidate_info" in data
    assert "onboarding_plan" in data
    assert "policy_answers" in data

if __name__ == "__main__":
    pytest.main([__file__])
```

Run tests:
```bash
pytest test_orchestrator.py
```

---

## 📈 Monitoring

### Enable Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@app.post("/orchestrate")
async def orchestrate_workflow(input_data: OrchestratorRequest):
    logger.info(f"Processing candidate for role: {input_data.job_role}")
    # ... rest of code
```

### View Logs

```bash
# Run with logging output
uvicorn orchestrator:app --port 9000 --log-level info

# Or redirect to file
uvicorn orchestrator:app --port 9000 > orchestrator.log 2>&1
```

---

##  Development Mode

Run with auto-reload for development:

```bash
uvicorn orchestrator:app --reload --port 9000 --log-level debug
```

This will:
- Auto-reload on code changes
- Show detailed debug logs
- Help during development

---

## Production Deployment

### Using Gunicorn (Recommended)

```bash
pip install gunicorn

gunicorn orchestrator:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:9000 \
  --timeout 120
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "orchestrator:app", "--host", "0.0.0.0", "--port", "9000"]
```

Build and run:

```bash
docker build -t hr-orchestrator .
docker run -p 9000:9000 hr-orchestrator
```

---

##  API Documentation

Once running, access interactive documentation at:

- **Swagger UI:** http://localhost:9000/docs
- **ReDoc:** http://localhost:9000/redoc
- **OpenAPI JSON:** http://localhost:9000/openapi.json

---

##  Next Steps

1. **Add authentication** for secure access
2. **Implement rate limiting** to prevent abuse
3. **Add batch processing** for multiple resumes
4. **Create frontend UI** for easier interaction
5. **Add webhook support** for async notifications
6. **Implement caching** for better performance
7. **Add integration with Google Calendar or Notion** for organisation of onboarding schedule

---

##  Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Verify all dependencies are installed
4. Check logs for error messages

---

##  License

This project is for educational and demonstration purposes.

---

**Last Updated:** October 2025  
**Version:** 1.0  
**Port:** 9000  
**Status:** Production Ready

for swagger ui: https://<codespace name>-9000.app.github.dev/docs#/default/orchestrate_workflow_orchestrate_post