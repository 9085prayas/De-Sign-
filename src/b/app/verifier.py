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
from typing import List, Tuple, Dict, Any

# --- 1. Configuration and Setup ---

# Set up structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up a cache to store results for 1 hour (3600 seconds)
cache = TTLCache(maxsize=100, ttl=3600)


# --- 2. Text Extraction Functions ---

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text from a PDF file."""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "".join(page.extract_text() for page in pdf_reader.pages)
        logging.info("Successfully extracted text from PDF.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extracts text from a DOCX file."""
    try:
        document = Document(io.BytesIO(docx_bytes))
        text = "\n".join([para.text for para in document.paragraphs])
        logging.info("Successfully extracted text from DOCX.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text from an image using OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        logging.info("Successfully extracted text from image using OCR.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from image with OCR: {e}")
        return ""


# --- 3. AI Analysis and Feature Functions ---

def generate_hackathon_llm_prompt(
    contract_text: str,
    clauses_to_check: List[str],
    company_risk_appetite: str,
    counterparty_type: str,
    selected_regulations: List[str],
    playbook_clauses: Dict[str, str],
    all_policy_texts: List[str] # New: Combined policy texts
) -> str:
    """
    Constructs an advanced prompt for LLM, incorporating company profile,
    regulations, a custom playbook, and additional policy texts for contextual risk assessment.
    """
    clauses_list_str = ", ".join(f'"{clause}"' for clause in clauses_to_check)
    
    # Add company context to the prompt
    company_context = (
        f"The user's company has a '{company_risk_appetite}' risk appetite. "
        f"The counterparty is identified as a '{counterparty_type}'. "
        f"Assess risks from the perspective of the user's company, considering this context."
    )

    # Add regulations to the prompt
    regulations_context = ""
    if selected_regulations:
        regulations_str = ", ".join(selected_regulations)
        regulations_context = (
            f"The contract must also comply with the following regulations: {regulations_str}. "
            f"Identify any non-compliance issues and justify."
        )

    # Add playbook clauses to the prompt
    playbook_context = ""
    if playbook_clauses:
        playbook_items = []
        for clause, text in playbook_clauses.items():
            playbook_items.append(f"'{clause}': '{text}'")
        playbook_context = (
            "The user's company has preferred 'playbook' language for some clauses. "
            "If a clause is present, compare it against the provided playbook text. "
            "Flag significant deviations and suggest how the contract's language differs from the playbook. "
            "Playbook clauses are: {" + ", ".join(playbook_items) + "}"
        )

    # Add all policy texts to the prompt
    policy_text_context = ""
    if all_policy_texts:
        combined_policy_text = "\n\n---\n\n".join(all_policy_texts)
        policy_text_context = (
            "In addition to the above, please also ensure the contract complies with the following internal company policies/guidelines. "
            "Refer to their text for specific requirements, and flag any non-compliance.\n"
            f"--- POLICIES/GUIDELINES TEXT ---\n{combined_policy_text}\n--- END POLICIES/GUIDELINES TEXT ---"
        )

    prompt = f"""
    You are an expert AI paralegal specializing in contract risk analysis for high-stakes corporate agreements.
    {company_context}
    {regulations_context}
    {playbook_context}
    {policy_text_context}

    **Instructions (Chain of Thought):**
    1.  **Contextual Understanding**: Read the entire contract to grasp its purpose, factoring in the company's risk appetite, counterparty type, and any provided policies/guidelines.
    2.  **Clause-by-Clause Analysis**: For each clause in the list [{clauses_list_str}], perform these steps:
        a.  **Locate & Cite**: Find the relevant text for the clause. Quote the single most pertinent sentence. If the clause is not present, indicate so.
        b.  **Analyze & Justify**: Determine if the clause is functionally present. Justify your decision.
        c.  **Risk Assessment**: Critically evaluate the clause's language, considering the company's risk appetite, counterparty, selected regulations, and uploaded/provided policies. Assign a risk level ('Low', 'Medium', 'High') and a numerical risk score (1-10, where 10 is highest risk). Explain why. A 'High' risk clause (or missing clause) might be one-sided, ambiguous, non-standard, or non-compliant with selected regulations/policies. If a playbook clause was provided, explicitly state if the contract's clause deviates and how.
        d.  **Confidence Score**: Assign a confidence score (0.0 to 1.0) for your analysis of this clause.
    3.  **Final Compilation**: Assemble all findings into a single, valid JSON object.

    **Output Format:**
    Respond ONLY with a valid JSON object. The JSON object must have a single key "analysis" which is an array of objects, each with the following structure:
    {{
      "clause_name": "Name of the Clause",
      "is_present": boolean,
      "confidence_score": float,
      "risk_level": "Low | Medium | High",
      "numerical_risk_score": int, # New: 1-10
      "justification": "Your brief analysis of the clause, its potential risks in context, and any deviations from playbook/regulations/policies.",
      "cited_text": "The most relevant quote from the contract if present, otherwise an empty string."
    }}

    ---
    **CONTRACT TEXT:**
    ---
    {contract_text}
    """
    return prompt

@cached(cache)
async def analyze_contract_text(
    contract_text: str,
    api_key: str,
    clauses_to_check: Tuple[str, ...], # Expects a Tuple for caching
    company_risk_appetite: str,
    counterparty_type: str,
    selected_regulations: Tuple[str, ...], # Expects a Tuple for caching
    playbook_clauses: Tuple[Tuple[str, str], ...], # Expects a Tuple of Tuples for caching
    all_policy_texts: Tuple[str, ...] # New: Combined policy texts as Tuple for caching
) -> Dict[str, Any]:
    """
    Asynchronously analyzes contract text using the Gemini LLM with an advanced prompt,
    incorporating dynamic clauses and contextual parameters.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Convert tuples back to lists/dict for prompt generation
        prompt = generate_hackathon_llm_prompt(
            contract_text=contract_text,
            clauses_to_check=list(clauses_to_check),
            company_risk_appetite=company_risk_appetite,
            counterparty_type=counterparty_type,
            selected_regulations=list(selected_regulations),
            playbook_clauses=dict(playbook_clauses), # Convert back to dict
            all_policy_texts=list(all_policy_texts) # Convert back to list
        )
        
        logging.info("Generating content with Gemini API using advanced contextual prompt...")
        # CRITICAL FIX: Ensure contents and generation_config are passed as separate keyword arguments
        response = await model.generate_content_async(
            contents=[{"role": "user", "parts": [{"text": prompt}]}], # Ensure it's a list of dicts for contents
            generation_config={"temperature": 0.0} # Set temperature to 0.0 for deterministic JSON output
        )
        
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

async def generate_clause_suggestion(clause_name: str, api_key: str, risky_text: str = "", context: str = "") -> str:
    """
    Generates a standard, legally sound clause suggestion,
    optionally considering the original risky text and additional context.
    """
    try:
        genai.configure(api_key=api_key)
        prompt_action = "is missing from a contract. Please draft a standard, fair, and legally sound version of this clause."
        if risky_text:
            prompt_action = f"is one-sided or risky. Please rewrite it to be more balanced and fair. Here is the original text:\n---{risky_text}\n---"

        full_prompt = f"You are an expert AI contract lawyer. The following clause, '{clause_name}', {prompt_action}"
        if context:
            full_prompt += f"\nConsider the following context when generating the suggestion: {context}"
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(full_prompt)
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

async def generate_overall_risk_summary(contract_text: str, analysis_results: Dict[str, Any], company_risk_appetite: str, api_key: str) -> str:
    """
    Generates an executive-level summary of the contract's overall risk profile
    based on the detailed analysis and company's risk appetite.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare a summary of the high/medium risks to feed into this prompt
        risk_points = []
        for item in analysis_results.get("analysis", []):
            if item.get("risk_level") in ["High", "Medium"]:
                risk_points.append(f"- {item['clause_name']} (Risk: {item['risk_level']}, Score: {item.get('numerical_risk_score', 'N/A')}): {item['justification']}")
        
        risk_summary_text = "\n".join(risk_points) if risk_points else "No significant high or medium risks identified in the specific clauses."

        prompt = f"""
        You are an expert AI legal risk analyst. Provide an executive-level summary (2-3 short paragraphs) of the key risks and overall risk profile for the following contract, from the perspective of a company with a '{company_risk_appetite}' risk appetite.
        Highlight the most critical issues and their potential impact.

        ---
        CONTRACT TEXT:
        {contract_text[:2000]}... # Limit text length for summary prompt
        ---

        ---
        DETECTED RISKS IN SPECIFIC CLAUSES:
        {risk_summary_text}
        ---

        Focus on the strategic implications of these risks for the company.
        """
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Error generating overall risk summary: {e}")
        return "Error: Could not generate overall risk summary."

async def extract_key_terms_and_obligations(contract_text: str, api_key: str) -> Dict[str, Any]:
    """
    Extracts key structured terms and obligations from the contract text using an LLM
    with a JSON schema for reliable output.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Define the JSON schema for structured output
        response_schema = {
            "type": "object",
            "properties": {
                "effective_date": {"type": "string", "description": "The date the contract becomes active, if present. Format YYYY-MM-DD."},
                "termination_date": {"type": "string", "description": "The date the contract is set to expire, if present. Format YYYY-MM-DD."},
                "renewal_term": {"type": "string", "description": "Details about automatic renewal or renewal notice periods, if present."},
                "contract_value": {"type": "string", "description": "The monetary value of the contract, if specified. Include currency."},
                "parties_involved": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of all primary parties to the contract."
                },
                "governing_law": {"type": "string", "description": "The jurisdiction whose laws govern the contract, if specified."},
                "payment_terms_summary": {"type": "string", "description": "A summary of payment schedules, due dates, or methods."},
                "key_obligations_for_party_A": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key duties or deliverables for the first identified party (e.g., 'Vendor's obligations')."
                },
                "key_obligations_for_party_B": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key duties or deliverables for the second identified party (e.g., 'Client's obligations')."
                },
                "brief_description": {"type": "string", "description": "A very brief (one sentence) overall description of the contract's purpose."}
            },
            "required": ["parties_involved", "brief_description"] # Essential fields
        }

        # The contents for the LLM call
        contents_for_llm = [{
            "role": "user",
            "parts": [{
                "text": f"""
                You are an expert contract analyst. Extract the following key terms and obligations from the provided contract text.
                If a field is not found, return null for that field.

                ---
                CONTRACT TEXT:
                {contract_text}
                """
            }]
        }]
        
        # The generationConfig for structured output as per instructions
        generation_config_for_llm = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }

        # CORRECTED: Pass contents and generation_config as separate keyword arguments
        response = await model.generate_content_async(
            contents=contents_for_llm,
            generation_config=generation_config_for_llm
        )
        
        # Access the text from the response candidate
        response_text = response.candidates[0].content.parts[0].text
        return json.loads(response_text)

    except json.JSONDecodeError:
        logging.error("Failed to decode JSON from LLM response for key terms extraction.")
        logging.debug(f"Raw LLM Response for key terms: {response.candidates[0].content.parts[0].text}")
        return {"error": "Could not extract key terms in expected JSON format."}
    except Exception as e:
        logging.error(f"Error extracting key terms and obligations: {e}")
        return {"error": f"Error during key term extraction: {e}"}

# Removed: async def answer_contract_question(contract_text: str, user_question: str, api_key: str) -> str:
# Removed:     """Answers a user's question based only on the provided contract text."""
# Removed:     try:
# Removed:         genai.configure(api_key=api_key)
# Removed:         prompt = f"""
# Removed:         You are an AI assistant answering questions about a legal contract. 
# Removed:         Use ONLY the provided contract text below to answer the user's question.
# Removed:         If the answer is not in the text, state that clearly by saying "I could not find an answer to that question in the provided document."
# Removed:         Do not use any external knowledge. Be concise.
# Removed: 
# Removed:         ---
# Removed:         CONTRACT TEXT:
# Removed:         {contract_text}
# Removed:         ---
# Removed: 
# Removed:         USER QUESTION:
# Removed:         {user_question}
# Removed:         """
# Removed:         model = genai.GenerativeModel('gemini-1.5-flash')
# Removed:         response = await model.generate_content_async(prompt)
# Removed:         return response.text
# Removed:     except Exception as e:
# Removed:         logging.error(f"An unexpected error occurred during Q&A: {e}")
# Removed:         return "Error: Could not process the question."


# --- 4. Main Entrypoint Function ---

async def verify_contract_clauses(
    file_bytes: bytes,
    content_type: str,
    api_key: str,
    clauses_to_check: List[str],
    company_risk_appetite: str,
    counterparty_type: str,
    selected_regulations: List[str],
    playbook_clauses_dict: Dict[str, str],
    all_policy_texts: List[str], # All policy-related text combined here
) -> Dict[str, Any]:
    """
    Main function to verify a contract. It extracts text and sends it for AI analysis,
    including new contextual parameters and orchestrating additional AI calls.
    """
    text = ""
    if content_type == "application/pdf":
        text = extract_text_from_pdf(file_bytes)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_text_from_docx(file_bytes)
    elif content_type in ["image/jpeg", "image/png", "image/jpg"]: # Added 'image/jpg'
        text = extract_text_from_image(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {content_type}")

    if not text:
        return {"error": "Could not extract any text from the uploaded file."}

    # Convert mutable inputs to immutable for caching
    hashable_clauses_to_check = tuple(clauses_to_check)
    hashable_selected_regulations = tuple(selected_regulations)
    hashable_playbook_clauses = tuple(sorted(playbook_clauses_dict.items())) # Sort items for consistent tuple order
    hashable_all_policy_texts = tuple(all_policy_texts) # Convert combined policy texts

    # Orchestrate the main analysis
    clause_analysis = await analyze_contract_text(
        contract_text=text,
        api_key=api_key,
        clauses_to_check=hashable_clauses_to_check,
        company_risk_appetite=company_risk_appetite,
        counterparty_type=counterparty_type,
        selected_regulations=hashable_selected_regulations,
        playbook_clauses=hashable_playbook_clauses,
        all_policy_texts=hashable_all_policy_texts # Pass combined policy texts
    )
    
    # Orchestrate additional AI calls
    executive_summary = await generate_overall_risk_summary(
        contract_text=text,
        analysis_results=clause_analysis,
        company_risk_appetite=company_risk_appetite,
        api_key=api_key
    )

    key_terms = await extract_key_terms_and_obligations(
        contract_text=text,
        api_key=api_key
    )

    return {
        "analysis": clause_analysis.get("analysis", []),
        "executive_summary": executive_summary,
        "key_terms_and_obligations": key_terms,
        "contract_text": text # Also return full text for Q&A
    }