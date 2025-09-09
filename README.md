# 📜 De-Sign: An Autonomous AI Agent Workflow for Contract Analysis

**De-Sign** is an advanced, autonomous multi-agent system designed to streamline and automate the entire contract lifecycle. It leverages a sophisticated workflow engine (LangGraph) to coordinate specialized AI agents that handle document analysis, risk assessment, digital signing, and scheduling, with built-in pauses for human-in-the-loop approvals.

---

## 🏆 Hackathon Submission
- **Team Name:** ALT+F4  
- **Team Members:** Prayas Chaware, Rishabh Parihar, Jay Gheewala, Punit Chaurasia, Laxman Rathod 
- **Hackathon Challenge Addressed:** Productivity & The Future of Work. This project showcases an autonomous system that significantly reduces manual effort, minimizes errors, and accelerates the contract approval process, representing the future of automated professional services.

---

## ✨ What We Built
De-Sign is a stateful, multi-agent application orchestrated by LangGraph. The system manages a document's journey from initial upload to final scheduling through a series of specialized agents, pausing for critical human intervention when necessary.

### The Autonomous Agents:
- ## Agent B (The Analyst):
  - Function: Ingests a document (.pdf, .docx, .png, etc.) and performs a deep risk analysis.
  - Intelligence: Utilizes a Retrieval-Augmented Generation (RAG) pipeline with Gemini and a Pinecone vector database (containing the company's legal playbook) to identify and score risks for key legal clauses.

- ## Agent C (The Signer):
  - Function: Once a human operator approves the analysis, this agent digitally signs the document.
  - Process: It generates a document hash and a unique digital signature, embedding them into the workflow's state to ensure integrity.

- ## Agent D (The Scheduler):
  - Function: After the document is signed and a human provides a meeting date, this agent schedules the final review meeting.
  - Process: It simulates creating a calendar event, generating a meeting ID, and confirming the schedule, marking the end of the workflow.

### The Workflow Engine:
The entire process is managed by a LangGraph state machine, which directs the flow of data between agents and pauses the workflow at two key checkpoints:

1. Approval Checkpoint: After Agent B's analysis, the workflow halts and waits for a user to approve or reject the risk assessment.

2. Date Input Checkpoint: After Agent C signs the document, the workflow halts again, waiting for a user to provide a date for the final meeting.

---

## 🚀 How to Run It

### 1. Prerequisites:
- Python **3.9+**
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and added to your system PATH
- Git

### 2. Clone the Repository:
```bash
git clone [Your-Public-GitHub-Repo-Link]
cd [repository-folder-name]
```
### 3. Set Up Environment Variables:
Create a `.env` file in the project root and add your API keys:
```bash
GEMINI_API_KEY="your-google-gemini-api-key"
PINECONE_API_KEY="your-pinecone-api-key"
DESCOPE_PROJECT_ID="your-descope-project-id"
```
### 4. Install Dependencies:
It’s recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate     # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
### 5. Ingest Your Legal Playbook:
This is a critical one-time setup step to populate the vector database with your company's legal standards, which Agent B relies on.

- Place your company's legal playbook documents (in .pdf format) inside the playbooks/ directory.
- Run the ingestion script:
```bash
python ingest_playbook.py
```
### 6. Run the Application
The backend is a Flask application that manages the agent workflow.
```bash
flask run --host=0.0.0.0 --port=5000
```
The API server will be available at http://127.0.0.1:5000. You can interact with it using API tools like Postman or a custom frontend.

---

### 🛠️ Tech Stack
- Agent & Workflow Orchestration: LangGraph
- Generative AI:
  - Reasoning & Analysis (Agent B): Google Gemini 1.5 Flash
  - Embeddings: Google text-embedding-004
- Vector Database: Pinecone for the RAG knowledge base.
- Backend Server: Flask
- Authentication: Descope for securing API endpoints.
- Document Processing: PyPDF2, python-docx, Pytesseract (for OCR)
  
---

### 🎥 Demo
👉 Watch the Demo Video
[Link to Your Demo Video on YouTube/Loom/etc.]

---

### 🚀 What We'd Do With More Time
- Introduce a "Reviewer" Agent (Agent A): Add a preliminary agent to review the analysis from Agent B and provide a second layer of validation or suggest minor automated edits before presenting to the human for approval.
- Frontend UI for Workflow Tracking: Build a dedicated Streamlit or React frontend to visualize the workflow's progress in real-time, showing which agent is currently active and what inputs are needed.
- Enhanced Tool Usage: Equip agents with more tools, such as the ability to send email notifications (e.g., Agent D notifying attendees) or to directly edit documents.
- Dynamic Agent Delegation: Implement a "Master Agent" that can dynamically decide which specialized agent to route tasks to based on the content of the document, rather than following a fixed graph.




