from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from .security import require_scope
from .verifier import extract_text_from_pdf, verify_contract_clauses

router = APIRouter()

@router.post("/verify")
@require_scope("contract.verify:clauses")
async def verify_document(request: Request, file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is accepted.")
    
    try:
        # Read the file content
        pdf_bytes = await file.read()
        
        # Extract text from the PDF
        contract_text = extract_text_from_pdf(pdf_bytes)
        if not contract_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
            
        # Verify the clauses
        verification_result = verify_contract_clauses(contract_text)
        
        return verification_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during verification: {str(e)}")
    