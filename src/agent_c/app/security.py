# security.py

import os
import logging
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from descope import DescopeClient, AuthException

# --- 1. Configuration and Setup ---

# Set up structured logging for better debugging in production
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    # Initialize the Descope client with the Project ID from environment variables.
    # This is done once when the application starts for efficiency.
    DESCOPE_PROJECT_ID = os.environ.get("DESCOPE_PROJECT_ID")
    if not DESCOPE_PROJECT_ID:
        raise ValueError("DESCOPE_PROJECT_ID environment variable is not set.")
    
    descope_client = DescopeClient(project_id=DESCOPE_PROJECT_ID)
    logging.info("Descope client initialized successfully.")

except ValueError as e:
    # This is a critical failure. The application cannot proceed without the client.
    logging.critical(f"FATAL: Descope client failed to initialize: {e}")
    descope_client = None

# This defines the "Bearer" token security scheme, which enables the "Authorize"
# button and lock icon in the FastAPI/Swagger UI documentation.
security_scheme = HTTPBearer()


# --- 2. DEPENDENCY FACTORY: The Reusable Security Guard ---

def require_scope(required_scope: str):
    """
    This is a dependency factory. It's a function that returns another function.
    This pattern allows you to create a customized security check for each endpoint
    by specifying the required permission (scope).
    
    Args:
        required_scope (str): The specific permission string required to access an endpoint.
        
    Returns:
        A FastAPI dependency function that validates a token and checks for the scope.
    """
    def security_decorator(token: str = Depends(security_scheme)):
        """
        This is the actual dependency that will be injected into your API endpoints.
        It validates the token and checks for the required permission.
        """
        if not descope_client:
            logging.error("Authentication check failed because Descope client is not configured.")
            raise HTTPException(
                status_code=503, detail="Authentication service is not available."
            )
        
        try:
            # Use the SDK's validate_permissions method. It's a single, secure call
            # that handles all complex validation:
            # 1. Checks the token's signature against Descope's public keys.
            # 2. Verifies the token has not expired.
            # 3. Validates the token's claims (issuer, audience).
            # 4. Confirms the required permission (scope) is present in the token.
            jwt_response = descope_client.validate_permissions(
                session_token=token.credentials, 
                permissions=[required_scope]
            )
            
            user_id = jwt_response.get("token", {}).get("sub")
            logging.info(f"Successfully validated token for user '{user_id}' with scope '{required_scope}'.")
            return jwt_response

        except AuthException as e:
            # The SDK raises a single AuthException for any validation failure.
            logging.warning(f"Token validation failed: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    return security_decorator