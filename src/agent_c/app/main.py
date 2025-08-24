# services/signatory/app/main.py

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router

app = FastAPI(
    title="Signatory Agent",
    description="An agent for performing a signing action on a document, secured by Descope.",
    version="1.0.0"
)

# CORS Middleware to allow requests from your frontend
origins = [
    "http://localhost",
    "http://localhost:3000", # For React dev server
    "http://localhost:8501", # For your Streamlit test app
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router with a versioned prefix
app.include_router(api_router, prefix="/api/v1", tags=["Signing"])

@app.get("/", tags=["Health Check"])
def read_root():
    """A simple health check endpoint."""
    return {"status": "Signatory Agent is running"}