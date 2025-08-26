from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging # Import logging

# Configure logging for the API
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Import all necessary functions from your verifier files
# Removed: from .security import require_scope (as Descope is removed)
from verifier import (
    extract_text_from_pdf, # Need these for processing policy files in the API
    extract_text_from_docx,
    extract_text_from_image,
    verify_contract_clauses,
    generate_clause_suggestion,
    generate_plain_english_summary,
    # Removed: answer_contract_question
)

# --- API Router Setup ---
router = APIRouter()

# Define the list of file types the API will accept
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "image/jpeg",
    "image/png",
    "image/jpg" # Added .jpg support
]

# --- Default Clauses (Consistent with app.py) ---
DEFAULT_CLAUSES_TO_CHECK = [
    "Indemnification", "Limitation of Liability", "Intellectual Property Rights",
    "Confidentiality", "Termination for Cause", "Governing Law & Jurisdiction",
    "Data Privacy & Security", "Force Majeure", "Payment Terms", "Warranties" # Added more common clauses
]

# --- Pydantic Models for Request Bodies ---

class SummarizeRequest(BaseModel):
    contract_text: str

class SuggestionRequest(BaseModel):
    clause_name: str
    risky_text: Optional[str] = ""
    context: Optional[str] = ""

# Removed: class QuestionRequest(BaseModel):
# Removed:    contract_text: str
# Removed:    question: str

# --- Dependency to get the Gemini API Key ---
# This remains, as Gemini API key is essential for AI functionality
async def get_gemini_api_key(x_api_key: str = Header(...)):
    """A dependency to extract the Gemini API key from the request header."""
    if not x_api_key:
        raise HTTPException(status_code=400, detail="X-API-Key header is required.")
    return x_api_key


# --- API Endpoints ---

@router.post(
    "/verify",
    summary="Analyze a contract document for high-risk clauses with contextual settings"
    # Removed: dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def verify_document(
    gemini_api_key: str = Depends(get_gemini_api_key),
    file: UploadFile = File(...),
    company_risk_appetite: str = Form("Moderate"),
    counterparty_type: str = Form("Large Enterprise Client"),
    selected_regulations: str = Form("None"),
    playbook_rules_str: str = Form(""),
    user_custom_clauses_str: Optional[str] = Form(""),
    policy_files: Optional[List[UploadFile]] = File(None),
    sidebar_policy_text: Optional[str] = Form("")
) -> Dict[str, Any]:
    """
    Accepts a main contract file, contextual settings, and optional policy documents/text input.
    Extracts text and uses AI to perform a detailed, contextual risk analysis.
    Returns a comprehensive analysis including executive summary, key terms,
    and detailed clause breakdowns.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logging.warning(f"Unsupported main contract file type uploaded: {file.content_type}")
        raise HTTPException(status_code=400, detail="Unsupported main contract file type.")
    
    try:
        main_contract_file_bytes = await file.read()

        # --- Process Policy Documents & Text Input ---
        all_policy_texts = []
        if policy_files:
            for policy_file in policy_files:
                policy_file_bytes = await policy_file.read()
                policy_content_type = policy_file.content_type
                
                policy_text = ""
                if policy_content_type == "application/pdf":
                    policy_text = extract_text_from_pdf(policy_file_bytes)
                elif policy_content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    policy_text = extract_text_from_docx(policy_file_bytes)
                elif policy_content_type in ["image/jpeg", "image/png", "image/jpg"]: # Also support jpg for policies
                    policy_text = extract_text_from_image(policy_file_bytes)
                
                if policy_text:
                    all_policy_texts.append(f"--- Policy Document: {policy_file.filename} ---\n{policy_text}")
                else:
                    logging.warning(f"Could not extract text from policy file: {policy_file.filename}")
        
        if sidebar_policy_text:
            all_policy_texts.append(f"--- User Provided Policy Text ---\n{sidebar_policy_text}")

        # --- Process Clause Selection ---
        all_clauses_to_check = list(DEFAULT_CLAUSES_TO_CHECK)
        if user_custom_clauses_str:
            custom_clauses = [c.strip() for c in user_custom_clauses_str.split(',') if c.strip()]
            all_clauses_to_check.extend(custom_clauses)
        all_clauses_to_check = sorted(list(set(all_clauses_to_check))) # Remove duplicates and sort

        if not all_clauses_to_check:
            raise HTTPException(status_code=400, detail="No clauses selected for verification. Please add some.")

        # --- Process Regulations ---
        parsed_regulations = [reg.strip() for reg in selected_regulations.split(',') if reg.strip() and reg.strip() != "None"]
        
        # --- Process Playbook Rules ---
        playbook_clauses_dict = {}
        if playbook_rules_str:
            for line in playbook_rules_str.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    playbook_clauses_dict[key.strip()] = value.strip()

        # Call the enhanced verify_contract_clauses function from verifier.py
        verification_result = await verify_contract_clauses(
            file_bytes=main_contract_file_bytes,
            content_type=file.content_type,
            api_key=gemini_api_key,
            clauses_to_check=all_clauses_to_check,
            company_risk_appetite=company_risk_appetite,
            counterparty_type=counterparty_type,
            selected_regulations=parsed_regulations,
            playbook_clauses_dict=playbook_clauses_dict,
            all_policy_texts=all_policy_texts # Pass all combined policy texts to verifier.py
        )
        
        if "error" in verification_result:
            logging.error(f"Error from verifier: {verification_result['error']}")
            raise HTTPException(status_code=400, detail=verification_result["error"])
            
        return verification_result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"An unexpected server error occurred during /verify: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@router.post(
    "/summarize",
    summary="Generate a plain English summary of a contract"
    # Removed: dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def summarize_contract(
    request: SummarizeRequest,
    gemini_api_key: str = Depends(get_gemini_api_key)
) -> Dict[str, str]:
    """
    Takes contract text and returns a simple, easy-to-understand summary.
    """
    try:
        summary = await generate_plain_english_summary(request.contract_text, gemini_api_key)
        return {"summary": summary}
    except Exception as e:
        logging.error(f"An unexpected server error occurred during /summarize: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@router.post(
    "/suggest-clause",
    summary="Get an AI-generated suggestion for a clause"
    # Removed: dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def suggest_clause_fix(
    request: SuggestionRequest,
    gemini_api_key: str = Depends(get_gemini_api_key)
) -> Dict[str, str]:
    """
    Generates a standard, legally-sound version of a missing or high-risk clause,
    optionally considering original risky text and additional context.
    """
    try:
        suggestion = await generate_clause_suggestion(
            clause_name=request.clause_name,
            risky_text=request.risky_text,
            api_key=gemini_api_key,
            context=request.context
        )
        return {"suggestion": suggestion}
    except Exception as e:
        logging.error(f"An unexpected server error occurred during /suggest-clause: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


# Removed: @router.post(
# Removed:     "/ask-question",
# Removed:     summary="Ask a question about the contract"
# Removed:     # Removed: dependencies=[Depends(require_scope("contract.verify:clauses"))]
# Removed: )
# Removed: async def ask_contract_question(
# Removed:     request: QuestionRequest,
# Removed:     gemini_api_key: str = Depends(get_gemini_api_key)
# Removed: ) -> Dict[str, str]:
# Removed:     """
# Removed:     Answers a user's natural language question based on the provided contract text.
# Removed:     """
# Removed:     try:
# Removed:         answer = await answer_contract_question(
# Removed:             contract_text=request.contract_text,
# Removed:             user_question=request.question,
# Removed:             api_key=gemini_api_key
# Removed:         )
# Removed:         return {"answer": answer}
# Removed:     except Exception as e:
# Removed:         logging.error(f"An unexpected server error occurred during /ask-question: {str(e)}", exc_info=True)
# Removed:         raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")