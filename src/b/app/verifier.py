import os
import io
import json
from PyPDF2 import PdfReader
import google.generativeai as genai


try:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=GOOGLE_API_KEY)
except ValueError as e:
    print(f"Error configuring Gemini: {e}")
    genai = None


CLAUSES_TO_CHECK = [
    "Confidentiality", "Limitation of Liability", "Governing Law",
    "Termination for Cause", "Indemnification", "Intellectual Property",
    "Dispute Resolution", "Force Majeure"
]

def extract_text_from_pdf(pdf_file: bytes) -> str:
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_file))
        text = "".join(page.extract_text() for page in pdf_reader.pages)
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def generate_advanced_llm_prompt(contract_text: str) -> str:
    """Constructs a more sophisticated prompt for the LLM."""
    clauses_list_str = ", ".join(f'"{clause}"' for clause in CLAUSES_TO_CHECK)
    
    prompt = f"""
    You are an expert AI paralegal. Your task is to meticulously analyze the provided contract text and verify the presence of key legal clauses.

    **Instructions:**
    1.  Read the entire contract text carefully.
    2.  For each clause in the required list [{clauses_list_str}], determine if its meaning and intent are present in the text.
    3.  If a clause is found, provide a brief justification and quote the most relevant sentence or phrase from the contract that supports your finding.
    4.  If a clause is not found, state that clearly.
    5.  Compile your findings into a single, valid JSON object.

    **Output Format:**
    Respond ONLY with a valid JSON object. Do not include any introductory text, explanations, or markdown formatting like ```json. The JSON object must have a single key "analysis" which is an array of objects. Each object in the array represents one of the required clauses and must have the following structure:
    {{
      "clause_name": "Name of the Clause",
      "is_present": boolean,
      "justification": "A brief explanation of why the clause is considered present or absent.",
      "cited_text": "The most relevant quote from the contract if the clause is present, otherwise an empty string."
    }}

    ---
    **CONTRACT TEXT:**
    ---
    {contract_text}
    """
    return prompt

def verify_clauses_with_llm(contract_text: str):

    if not genai:
        raise RuntimeError("Google Generative AI client is not configured. Is the GOOGLE_API_KEY set?")

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = generate_advanced_llm_prompt(contract_text)
        
        response = model.generate_content(prompt)
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        
        
        parsed_response = json.loads(response_text)
        
        analysis = parsed_response.get("analysis")
        if not isinstance(analysis, list):
            raise ValueError("LLM response is missing the 'analysis' array.")

        clauses_found = [item for item in analysis if item.get("is_present")]
        clauses_missing = [item for item in analysis if not item.get("is_present")]

        is_verified = len(clauses_missing) == 0
        summary = "All required clauses were successfully identified." if is_verified else f"Verification failed. Missing {len(clauses_missing)} clause(s)."

        return {
            "is_verified": is_verified,
            "summary": summary,
            "clauses_found": [{"clause": item["clause_name"], "justification": item["justification"], "cited_text": item["cited_text"]} for item in clauses_found],
            "clauses_missing": [{"clause": item["clause_name"], "justification": item["justification"]} for item in clauses_missing]
        }

    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from LLM response.")
        print("Raw LLM Response:", response.text)
        raise ValueError("The LLM returned a response that was not valid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred during LLM verification: {e}")
        raise
