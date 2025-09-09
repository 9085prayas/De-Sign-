De-Sign: AI Contract Co-Pilot
De-Sign is an intelligent AI-powered paralegal designed to accelerate contract review cycles. It analyzes legal documents, identifies high-risk clauses by comparing them against a company's internal legal playbook, suggests compliant alternatives, and translates complex legalese into plain English.

🏆 Hackathon Submission
Team Name: ALT+F4

Team Members:  Prayas Chaware,Rishabh Parihar,Jay Gheewala,Punit Chaurasia,Laxman Rathode

Hackathon Challenge Addressed: Productivity & The Future of Work. This project directly addresses improving the efficiency, accuracy, and accessibility of the legal review process, a key component of modernizing professional workflows.

✨ What We Built
De-Sign is a full-stack application that employs a sophisticated Retrieval-Augmented Generation (RAG) pipeline to provide context-aware, playbook-driven contract analysis.

Key Features:
Multi-Format Document Upload: Users can upload contracts in various formats, including .pdf, .docx, .png, and .jpeg. The system uses robust text extraction for each type, including Optical Character Recognition (OCR) for images.

Automated Risk Analysis: The application automatically scans the contract for a predefined set of crucial legal clauses (e.g., Indemnification, Limitation of Liability), which are dynamically identified from the company playbook during an ingestion step.

Playbook-Driven Compliance: The core of our system is a vector database (Pinecone) containing the company's legal playbook. For each clause found in a contract, the AI retrieves the relevant playbook guidance to perform an accurate compliance check.

Risk Scoring & Justification: Each clause is assigned a risk level (Low, Medium, High) with a detailed justification , explaining why it meets or fails to meet the company's standards, citing the specific text from the contract.

AI-Powered Clause Suggestions: For high-risk or missing clauses, users can click a button to have AI generate a balanced, compliant alternative based on the playbook's principles.

Plain English Summaries: With one click, the entire contract can be summarized into a simple, easy-to-understand overview, making it accessible to non-legal stakeholders.

How to Run It
1. Prerequisites:

Python 3.9+

Tesseract OCR installed and accessible in your system's PATH.

Git

2. Clone the Repository:

# First, create a new repository on GitHub.
# Then, clone it to your local machine.
git clone [Your-Public-GitHub-Repo-Link]
cd [repository-folder-name]

3. Set Up Environment Variables:
Create a file named .env in the root directory of the project and add your API keys:

GEMINI_API_KEY="your-google-gemini-api-key"
PINECONE_API_KEY="your-pinecone-api-key"

# Optional: For user authentication via Descope
# DESCOPE_PROJECT_ID="your-descope-project-id"

4. Install Dependencies:
It's recommended to use a virtual environment.

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# You will need to create a requirements.txt file first
# Run this command in your local environment where you developed the project:
# pip freeze > requirements.txt
pip install -r requirements.txt

5. Ingest Your Legal Playbook:
This is a critical one-time setup step to populate the vector database with your company's legal standards.

Place your company's legal playbook documents (in .pdf format) inside the playbooks/ directory.

Run the ingestion script. This will process the PDFs, use Gemini to identify key clause titles, generate embeddings, and store them in your Pinecone index. It will also auto-generate the clauses.json file used by the verifier.

python ingest_playbook.py

6. Run the Application:
The backend and frontend run as separate processes. You will need two terminal windows.

Terminal 1: Start the FastAPI Backend

uvicorn main:app --reload

The API will be available at http://127.0.0.1:8000.

Terminal 2: Start the Streamlit Frontend

streamlit run app.py

The web application will open automatically in your browser at http://127.0.0.1:8501.

🛠️ Tech Stack
Generative AI:

Reasoning & Analysis: Google Gemini 1.5 Flash

Embeddings: Google text-embedding-004

Vector Database: Pinecone for storing and retrieving legal playbook embeddings.

Backend: FastAPI for a robust, high-performance API.

Frontend: Streamlit for rapid, interactive UI development.

Document Processing:

PDF: PyPDF2

DOCX: python-docx

Images (OCR): pytesseract

Authentication : Descope for securing API endpoints.

🎥 Demo Video
See De-Sign in action!

[Link to Your Demo Video on YouTube/Loom/etc.]

🚀 What We'd Do With More Time
Full Contract Redlining: Integrate a "Track Changes" feature where users can accept, reject, or modify AI suggestions directly within the document viewer and then export a redlined .docx file.

Interactive Playbook Management UI: Build a secure web interface for the legal team to upload, manage, and update their playbook documents, making the RAG knowledge base easier to maintain without command-line access.

Comparative Analysis: Add a feature to compare two different versions of a contract, using AI to highlight and explain the material differences between them.

Clause Library: Create a centralized library of pre-approved, best-practice clauses that users can easily search and insert into contracts.

Deeper IDE Integration: Develop plugins for Microsoft Word or Google Docs to bring the AI co-pilot directly into the user's existing workflow, removing the need to switch applications.
