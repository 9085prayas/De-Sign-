# api.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

# Import all necessary functions from your verifier and security files
from .security import require_scope
from .verifier import (
    verify_contract_clauses,
    generate_clause_suggestion,
    generate_plain_english_summary,
    answer_contract_question
)

# --- API Router Setup ---
router = APIRouter()

# Define the list of file types the API will accept
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "image/jpeg",
    "image/png"
]

# --- Pydantic Models for Request Bodies ---

class SummarizeRequest(BaseModel):
    contract_text: str

class SuggestionRequest(BaseModel):
    clause_name: str
    risky_text: Optional[str] = ""

class QuestionRequest(BaseModel):
    contract_text: str
    question: str

# --- Dependency to get the Gemini API Key ---

async def get_gemini_api_key(x_api_key: str = Header(...)):
    """A dependency to extract the Gemini API key from the request header."""
    if not x_api_key:
        raise HTTPException(status_code=400, detail="X-API-Key header is required.")
    return x_api_key


# --- API Endpoints ---

@router.post(
    "/verify",
    summary="Analyze a contract document for high-risk clauses",
    dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def verify_document(
    gemini_api_key: str = Depends(get_gemini_api_key),
    file: UploadFile = File(...)
):
    """
    Accepts a file upload (PDF, DOCX, JPG, PNG), extracts its text,
    and uses an AI to perform a detailed risk analysis.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    try:
        file_bytes = await file.read()
        verification_result = await verify_contract_clauses(
            file_bytes=file_bytes,
            content_type=file.content_type,
            api_key=gemini_api_key
        )
        
        if "error" in verification_result:
            raise HTTPException(status_code=400, detail=verification_result["error"])
            
        return verification_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@router.post(
    "/summarize",
    summary="Generate a plain English summary of a contract",
    dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def summarize_contract(
    request: SummarizeRequest,
    gemini_api_key: str = Depends(get_gemini_api_key)
):
    """
    Takes contract text and returns a simple, easy-to-understand summary.
    """
    summary = await generate_plain_english_summary(request.contract_text, gemini_api_key)
    return {"summary": summary}


@router.post(
    "/suggest-clause",
    summary="Get an AI-generated suggestion for a clause",
    dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def suggest_clause_fix(
    request: SuggestionRequest,
    gemini_api_key: str = Depends(get_gemini_api_key)
):
    """
    Generates a standard, legally-sound version of a missing or high-risk clause.
    """
    suggestion = await generate_clause_suggestion(
        clause_name=request.clause_name,
        risky_text=request.risky_text,
        api_key=gemini_api_key
    )
    return {"suggestion": suggestion}


@router.post(
    "/ask-question",
    summary="Ask a question about the contract",
    dependencies=[Depends(require_scope("contract.verify:clauses"))]
)
async def ask_contract_question(
    request: QuestionRequest,
    gemini_api_key: str = Depends(get_gemini_api_key)
):
    """
    Answers a user's natural language question based on the provided contract text.
    """
    answer = await answer_contract_question(
        contract_text=request.contract_text,
        user_question=request.question,
        api_key=gemini_api_key
    )
    return {"answer": answer}

