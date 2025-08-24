from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router


from dotenv import load_dotenv
load_dotenv()

# --- Application Setup ---
app = FastAPI(
    title="Scrutinizer Agent",
    description="An agent for verifying document clauses, secured by Descope.",
    version="1.0.0"
)

# --- CORS Middleware ---
# This allows your future React frontend to make requests to this backend.
# In production, you should restrict the origins to your frontend's domain.
origins = [
    "http://localhost",
    "http://localhost:3000", # Default for React dev server
    "http://localhost:8501", # For your Streamlit test app
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# --- API Router ---
# Using a versioned prefix for the API
app.include_router(api_router, prefix="/api/v1", tags=["Verification"])

# --- Root Health Check ---
@app.get("/", tags=["Health Check"])
def read_root():
    """A simple health check endpoint to confirm the service is running."""
    return {"status": "Scrutinizer Agent is running"}









""" from fastapi import FastAPI
from .api import router as api_router

app = FastAPI(
    title="Scrutinizer Agent",
    description="An agent for verifying document clauses, secured by Descope.",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api", tags=["Verification"])

@app.get("/")
def read_root():
    return {"status": "Scrutinizer Agent is running"} """