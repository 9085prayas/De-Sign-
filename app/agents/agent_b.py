# In app/agents/agent_b.py

import os
import io
import json
import logging
import asyncio
from typing import Dict, Any

# --- Copied imports from your original verifier.py ---
from PIL import Image
import pytesseract
from docx import Document
from PyPDF2 import PdfReader
import google.generativeai as genai
from cachetools import cached, TTLCache
from pinecone import Pinecone

# --- Copied functions and setup from your original verifier.py ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_clauses_to_check() -> list[str]:
    """Loads the list of clauses from the JSON config file."""
    try:
        # Assumes clauses.json is in the project root, one level above the 'app' directory
        with open("../clauses.json", 'r') as f:
            clauses = json.load(f)
            logging.info(f"Successfully loaded {len(clauses)} clauses to check from clauses.json")
            return clauses
    except FileNotFoundError:
        logging.warning("clauses.json not found. Falling back to default list.")
        return [
            "Indemnification", "Limitation of Liability", "Intellectual Property Rights",
            "Confidentiality", "Termination for Cause", "Governing Law & Jurisdiction"
        ]

CLAUSES_TO_CHECK = load_clauses_to_check()
cache = TTLCache(maxsize=100, ttl=3600)
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
INDEX_NAME = "company-playbook"
EMBEDDING_MODEL = "models/text-embedding-004"
pinecone_index = None
try:
    if PINECONE_API_KEY:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        pinecone_index = pc.Index(INDEX_NAME)
        logging.info("Successfully connected to Pinecone index.")
    else:
        logging.warning("PINECONE_API_KEY not found. RAG features will be disabled.")
except Exception as e:
    logging.warning(f"Could not connect to Pinecone. RAG features will be disabled. Error: {e}")

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    return "".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())

def extract_text_from_docx(docx_bytes: bytes) -> str:
    document = Document(io.BytesIO(docx_bytes))
    return "\n".join([para.text for para in document.paragraphs])

def extract_text_from_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)

def retrieve_playbook_context(query: str, n_results: int = 3) -> str:
    if not pinecone_index:
        return "No playbook context available."
    try:
        query_embedding = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_query"
        )['embedding']

        results = pinecone_index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True
        )
        
        context = "\n---\n".join([match['metadata']['text'] for match in results['matches']])
        logging.info(f"Retrieved context for query: '{query[:50]}...'")
        return context
    except Exception as e:
        logging.error(f"Error retrieving from Pinecone: {e}")
        return "Failed to retrieve playbook context."

def generate_rag_llm_prompt(contract_text: str, playbook_context: str, clause_name: str) -> str:
    return f"""
    You are an expert AI paralegal specializing in contract risk analysis. Your primary goal is to ensure compliance with our company's legal playbook.

    **Instructions:**
    1.  **Analyze the Clause**: Read the provided clause text from the contract.
    2.  **Consult the Playbook**: Review the relevant sections from our company's legal playbook provided below.
    3.  **Compare and Assess Risk**: Compare the contract's clause against the playbook's guidance. Assign a risk level ('Low', 'Medium', 'High').
    4.  **Justify**: Clearly explain *why* the clause has the assigned risk level, referencing specific points from the playbook.
    5.  **Output Format**: Respond ONLY with a valid JSON object with the following structure:
        {{
          "clause_name": "{clause_name}",
          "is_present": boolean,
          "confidence_score": float,
          "risk_level": "Low | Medium | High",
          "justification": "Your analysis comparing the clause to the playbook.",
          "cited_text": "The most relevant quote from the contract if present, otherwise an empty string."
        }}

    ---
    **COMPANY PLAYBOOK CONTEXT for '{clause_name}':**
    ---
    {playbook_context}
    ---
    **CONTRACT TEXT:**
    ---
    {contract_text}
    """

@cached(cache)
async def analyze_contract_text(contract_text: str, api_key: str):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    all_analyses = []
    for clause_name in CLAUSES_TO_CHECK:
        logging.info(f"Analyzing clause: {clause_name}")
        playbook_context = retrieve_playbook_context(f"Company policy for {clause_name} clause")
        prompt = generate_rag_llm_prompt(contract_text, playbook_context, clause_name)
        response = await model.generate_content_async(prompt)
        try:
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            parsed_clause = json.loads(response_text)
            all_analyses.append(parsed_clause)
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logging.warning(f"Could not decode or parse response for clause '{clause_name}'. Error: {e}. Skipping.")
            all_analyses.append({
                "clause_name": clause_name,
                "is_present": False,
                "confidence_score": 0.5,
                "risk_level": "Medium",
                "justification": f"AI failed to produce a valid analysis for this clause. Raw response: {response.text[:100]}...",
                "cited_text": ""
            })
    return {"analysis": all_analyses}

async def verify_contract_clauses(file_bytes: bytes, content_type: str, api_key: str):
    text = ""
    if content_type == "application/pdf":
        text = extract_text_from_pdf(file_bytes)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_text_from_docx(file_bytes)
    elif content_type in ["image/jpeg", "image/png"]:
        text = extract_text_from_image(file_bytes)
    
    if not text or not text.strip():
        return {"error": "Could not extract any meaningful text from the uploaded file."}
        
    return await analyze_contract_text(text, api_key)


# --- The New AgentB Class Integrating Your Logic ---
class AgentB:
    """Risk Assessment Agent B - Powered by Gemini AI and RAG."""
    
    def __init__(self):
        self.agent_name = "Agent B - AI Contract Analysis"
        
    def analyze_file(self, file_path: str, additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyzes the uploaded file using the Gemini AI and RAG pipeline.
        This is the entry point called by the LangGraph workflow.
        """
        try:
            print(f"[{self.agent_name}] Starting AI analysis of: {os.path.basename(file_path)}")
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set.")

            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            _, extension = os.path.splitext(file_path)
            content_type_map = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'
            }
            content_type = content_type_map.get(extension.lower())
            if not content_type:
                return self._create_error_response(f"Unsupported file type: {extension}")

            # Run the async verification function
            analysis_result = asyncio.run(verify_contract_clauses(
                file_bytes=file_bytes,
                content_type=content_type,
                api_key=gemini_api_key
            ))

            if "error" in analysis_result:
                return self._create_error_response(analysis_result["error"])

            print(f"[{self.agent_name}] AI Analysis complete.")
            return analysis_result

        except Exception as e:
            logging.error(f"[{self.agent_name}] AI analysis failed: {e}", exc_info=True)
            return self._create_error_response(f"An unexpected error occurred during AI analysis: {e}")
            
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Creates a standardized error response for the workflow."""
        return {'error': error_message, 'analysis': []}