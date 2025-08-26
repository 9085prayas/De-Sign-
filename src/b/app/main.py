from fastapi import FastAPI
from .api import router as api_router

app = FastAPI(
    title="Agent-B",
    description="An agent for verifying document clauses, secured by Descope.",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api", tags=["Verification"])

@app.get("/")
def read_root():
    return {"status": "Agent-B is running"}
