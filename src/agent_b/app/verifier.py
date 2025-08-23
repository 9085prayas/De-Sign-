import io
from PyPDF2 import PdfReader
import re

REQUIRED_CLAUSES = {
    "Confidentiality": ["confidentiality", "confidential information", "nda"],
    "Limitation of Liability": ["limitation of liability", "liable for damages"],
    "Governing Law": ["governing law", "jurisdiction"],
    "Termination for Cause": ["termination for cause", "breach of contract"],
    "Indemnification": ["indemnify", "indemnification", "hold harmless"],
    "Intellectual Property": ["intellectual property", "ip rights", "ownership of work product"],
    "Dispute Resolution": ["dispute resolution", "arbitration", "mediation"],
    "Force Majeure": ["force majeure", "act of god"]
}

def extract_text(file : bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.lower()
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def verify_contract_clauses(text: str):
    clauses_found = []
    clauses_missing = []

    for clause_name, keywords in REQUIRED_CLAUSES.items():
        found = any(keyword in text for keyword in keywords)
        if found:
            clauses_found.append(clause_name)
        else:
            clauses_missing.append(clause_name)

    is_verified = len(clauses_missing) == 0
    
    summary = "All required clauses are present." if is_verified else f"Contract is missing {len(clauses_missing)} key clause(s)."

    return {
        "is_verified": is_verified,
        "clauses_found": clauses_found,
        "clauses_missing": clauses_missing,
        "summary": summary
    }

