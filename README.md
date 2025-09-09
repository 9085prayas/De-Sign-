# 📜 De-Sign: AI Contract Co-Pilot

**De-Sign** is an intelligent AI-powered paralegal designed to accelerate contract review cycles.  
It analyzes legal documents, identifies high-risk clauses by comparing them against a company's internal legal playbook, suggests compliant alternatives, and translates complex legalese into plain English.

---

## 🏆 Hackathon Submission
**Team Name:** ALT+F4  
**Team Members:** Prayas Chaware, Rishabh Parihar, Jay Gheewala, Punit Chaurasia, Laxman Rathode  
**Hackathon Challenge Addressed:** Productivity & The Future of Work.This project directly addresses improving the **efficiency, accuracy, and accessibility** of the legal review process — a key component of modernizing professional workflows.

---

## ✨ What We Built

De-Sign is a **full-stack application** employing a sophisticated **Retrieval-Augmented Generation (RAG)** pipeline for context-aware, playbook-driven contract analysis.

### 🔑 Key Features
- **Multi-Format Document Upload:** Supports `.pdf`, `.docx`, `.png`, `.jpeg` with OCR for images.  
- **Automated Risk Analysis:** Scans for crucial legal clauses (e.g., Indemnification, Liability).  
- **Playbook-Driven Compliance:** Cross-checks against company standards stored in a Pinecone vector DB.  
- **Risk Scoring & Justification:** Labels clauses as *Low, Medium, or High Risk* with detailed explanations.  
- **AI-Powered Clause Suggestions:** Generates compliant alternatives for missing or risky clauses.  
- **Plain English Summaries:** Summarizes entire contracts into easy-to-understand language.  

---

## 🚀 Getting Started

### 1. Prerequisites
- Python **3.9+**
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and added to your system PATH
- Git

### 2. Clone the Repository
```bash
git clone [Your-Public-GitHub-Repo-Link]
cd [repository-folder-name]
```
### 3. Environment Variables
Create a `.env` file in the project root and add your API keys:
```bash
GEMINI_API_KEY="your-google-gemini-api-key"
PINECONE_API_KEY="your-pinecone-api-key"
DESCOPE_PROJECT_ID="your-descope-project-id"
```
### 4. Install Dependencies
It’s recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate     # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
### 5. Ingest Legal Playbook
Place your company’s playbook PDFs in the playbooks/ directory. Then run:
```bash
python ingest_playbook.py
```
This will process documents, extract clause embeddings, and store them in Pinecone.
### 6. Run the Application
Open two terminals:
## Backend (FastAPI):
```bash
uvicorn main:app --reload
```
Runs at → http://127.0.0.1:8000
## Frontend (Streamlit):
```bash
streamlit run app.py
```
Opens at → http://127.0.0.1:8501

---

### 🛠️ Tech Stack
Generative AI:
- Reasoning: Google Gemini 1.5 Flash
- Embeddings: Google text-embedding-004
- Database: Pinecone (vector search)
  
Application:
- Backend: FastAPI
- Frontend: Streamlit

Document Processing:
- PDF: PyPDF2
- DOCX: python-docx
- OCR: pytesseract

Authentication:
- Descope

---

### 🎥 Demo
👉 Watch the Demo Video

---

### 🚀 Future Enhancements
- Full Contract Redlining: Track-changes support with exportable .docx
- Interactive Playbook Management: Secure UI for playbook updates
- Comparative Analysis: AI-powered diff between contract versions
- Clause Library: Pre-approved, searchable clause repository
- IDE/Docs Integration: Plugins for MS Word / Google Docs




