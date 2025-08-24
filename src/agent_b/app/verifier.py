# verifier.py

import os
import io
import json
import logging
from PIL import Image
import pytesseract
from docx import Document
from PyPDF2 import PdfReader
import google.generativeai as genai
from cachetools import cached, TTLCache
from typing import List, Tuple # Import Tuple for type hinting

# --- 1. Configuration and Setup ---

# Set up structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up a cache to store results for 1 hour (3600 seconds)
cache = TTLCache(maxsize=100, ttl=3600)


# --- 2. Text Extraction Functions ---

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "".join(page.extract_text() for page in pdf_reader.pages)
        logging.info("Successfully extracted text from PDF.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(docx_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(docx_bytes))
        text = "\n".join([para.text for para in document.paragraphs])
        logging.info("Successfully extracted text from DOCX.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        logging.info("Successfully extracted text from image using OCR.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from image with OCR: {e}")
        return ""


# --- 3. AI Analysis and Feature Functions ---

# Modified to accept clauses_to_check as a parameter
def generate_hackathon_llm_prompt(contract_text: str, clauses_to_check: List[str]) -> str:
    """Constructs a prompt that forces reasoning, risk scoring, and justifications for dynamic clauses."""
    clauses_list_str = ", ".join(f'"{clause}"' for clause in clauses_to_check)
    
    prompt = f"""
    You are an expert AI paralegal specializing in contract risk analysis for high-stakes corporate agreements.

    **Instructions (Chain of Thought):**
    1.  **Contextual Understanding**: Read the entire contract to grasp its purpose.
    2.  **Clause-by-Clause Analysis**: For each clause in the list [{clauses_list_str}], perform these steps:
        a.  **Locate & Cite**: Find the relevant text for the clause. Quote the single most pertinent sentence.
        b.  **Analyze & Justify**: Determine if the clause is functionally present. Justify your decision.
        c.  **Risk Assessment**: Critically evaluate the clause's language. Assign a risk level ('Low', 'Medium', 'High') and explain why. A 'High' risk clause might be one-sided, ambiguous, or non-standard. A missing clause is automatically 'High' risk.
        d.  **Confidence Score**: Assign a confidence score (0.0 to 1.0) for your analysis of this clause.
    3.  **Final Compilation**: Assemble all findings into a single, valid JSON object.

    **Output Format:**
    Respond ONLY with a valid JSON object. The JSON object must have a single key "analysis" which is an array of objects, each with the following structure:
    {{
      "clause_name": "Name of the Clause",
      "is_present": boolean,
      "confidence_score": float,
      "risk_level": "Low | Medium | High",
      "justification": "Your brief analysis of the clause and its potential risks.",
      "cited_text": "The most relevant quote from the contract if present, otherwise an empty string."
    }}

    ---
    **CONTRACT TEXT:**
    ---
    {contract_text}
    """
    return prompt

# Modified to accept clauses_to_check as a parameter. Now expects a hashable type.
@cached(cache)
async def analyze_contract_text(contract_text: str, api_key: str, clauses_to_check: Tuple[str, ...]): # Expects a Tuple
    """Asynchronously analyzes contract text using the Gemini LLM with the advanced prompt and dynamic clauses."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Pass clauses_to_check (which is now a tuple) to the prompt generation.
        # It's fine for prompt generation to convert it back to a list if needed internally,
        # as the cache key has already been generated based on the tuple.
        prompt = generate_hackathon_llm_prompt(contract_text, list(clauses_to_check))
        
        logging.info("Generating content with Gemini API using advanced prompt...")
        response = await model.generate_content_async(prompt)
        
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        parsed_response = json.loads(response_text)
        
        analysis = parsed_response.get("analysis")
        if not isinstance(analysis, list):
            raise ValueError("LLM response is missing the 'analysis' array.")

        return {"analysis": analysis}

    except json.JSONDecodeError:
        logging.error("Failed to decode JSON from LLM response.")
        logging.debug(f"Raw LLM Response: {response.text}")
        raise ValueError("The LLM returned a response that was not valid JSON.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during LLM verification: {e}")
        raise

async def generate_clause_suggestion(clause_name: str, api_key: str, risky_text: str = "") -> str:
    """Generates a standard, legally sound clause suggestion."""
    try:
        genai.configure(api_key=api_key)
        prompt_action = "is missing from a contract. Please draft a standard, fair, and legally sound version of this clause."
        if risky_text:
            prompt_action = f"is one-sided or risky. Please rewrite it to be more balanced and fair. Here is the original text:\n---{risky_text}\n---"

        prompt = f"You are an expert AI contract lawyer. The following clause, '{clause_name}', {prompt_action}"
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"An unexpected error occurred during clause suggestion: {e}")
        return "Error: Could not generate suggestion."


async def generate_plain_english_summary(contract_text: str, api_key: str) -> str:
    """Generates a simple, easy-to-understand summary of a contract."""
    try:
        genai.configure(api_key=api_key)
        prompt = f"""
        You are an expert at translating complex legal documents into simple, plain English. 
        Analyze the following contract and provide a concise summary (2-3 short paragraphs) that a non-lawyer can easily understand. 
        Focus on the key obligations for each party and the most significant risks.
        ---
        CONTRACT TEXT:
        {contract_text}
        """
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"An unexpected error occurred during summary generation: {e}")
        return "Error: Could not generate summary."

# --- NEW: Feature 1 - Interactive Q&A ---
async def answer_contract_question(contract_text: str, user_question: str, api_key: str) -> str:
    """Answers a user's question based only on the provided contract text."""
    try:
        genai.configure(api_key=api_key)
        prompt = f"""
        You are an AI assistant answering questions about a legal contract. 
        Use ONLY the provided contract text below to answer the user's question.
        If the answer is not in the text, state that clearly by saying "I could not find an answer to that question in the provided document."
        Do not use any external knowledge. Be concise.

        ---
        CONTRACT TEXT:
        {contract_text}
        ---

        USER QUESTION:
        {user_question}
        """
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"An unexpected error occurred during Q&A: {e}")
        return "Error: Could not process the question."


# --- 4. Main Entrypoint Function ---

# Modified to accept clauses_to_check as a parameter
async def verify_contract_clauses(file_bytes: bytes, content_type: str, api_key: str, clauses_to_check: List[str]):
    """
    Main function to verify a contract. It extracts text and sends it for AI analysis.
    Now accepts a dynamic list of clauses to check.
    """
    text = ""
    if content_type == "application/pdf":
        text = extract_text_from_pdf(file_bytes)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_text_from_docx(file_bytes)
    elif content_type in ["image/jpeg", "image/png"]:
        text = extract_text_from_image(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {content_type}")

    if not text:
        return {"error": "Could not extract any text from the uploaded file."}

    # Convert clauses_to_check to a tuple BEFORE passing it to the cached function
    hashable_clauses_to_check = tuple(clauses_to_check)
    
    # Pass the API key AND the hashable tuple to the analysis function
    return await analyze_contract_text(text, api_key, hashable_clauses_to_check)
