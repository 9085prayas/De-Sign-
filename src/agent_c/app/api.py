# services/signatory/app/api.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Import the security dependency and business logic
from .security import require_scope
from .signer import perform_signing_action

router = APIRouter()

# Define the expected request body
class SignRequest(BaseModel):
    contract_id: str

@router.post(
    "/sign-contract",
    # This dependency protects the endpoint, requiring the 'contract.sign' scope
    dependencies=[Depends(require_scope("contract.sign"))]
)
async def sign_contract(request: SignRequest):
    """
    Performs a signing action on a contract.
    Access requires the 'contract.sign' scope in the Descope token.
    """
    # Call the core signing logic from signer.py
    result_message = perform_signing_action(request.contract_id)
    
    return {"message": result_message}