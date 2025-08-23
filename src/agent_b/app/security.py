import os 
import requests 
from jose import JWTError , jwt
from fastapi import HTTPException , Request
from functools import wraps
from jose.utils import base64url_decode

DESCOPE_PROJECT_ID = os.getenv("DESCOPE_PROJECT_ID")
if not DESCOPE_PROJECT_ID : 
    raise RuntimeError("DESCOPE_PROJECT_ID is not set")

JWKS_URL = f"https://api.descope.com/{DESCOPE_PROJECT_ID}/.well-known/jwks.json" #checks all the keys that is needed for validation from .well-known

try : 
    response = requests.get(JWKS_URL)
    response.raise_for_status()
    jwks = response.json()
except requests.RequestException as e:
    raise RuntimeError(f"Failed to retrieve JWKS: {e}")


def get_tokens_from_header(request: Request) -> str: 
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = auth_header.split()
    if token[0].lower() != "bearer" or len(token) != 2:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    return token[1] 

def validate_jwt(token: str, required_scopes: str) -> dict:
    try :
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid token")
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token")

        payload = jwt.decode( #to decode and validate tokens
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=DESCOPE_PROJECT_ID, # Audience should be your Project ID
            issuer=f"https://api.descope.com/{DESCOPE_PROJECT_ID}"
        )
        scopes = payload.get("scope", "").split()
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied. Required scope: '{required_scope}'"
            )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Invalid claims: {e}")
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

def required_scope(required_scope: str):

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            token = get_tokens_from_header(request)
            validate_jwt(token, required_scope)
            return await func(request, *args, **kwargs)
    return decorator
