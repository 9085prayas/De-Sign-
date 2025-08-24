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




















    '''import streamlit as st
import os
import io
import json
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- Core Logic from verifier.py ---
# This section is adapted from your Agent B code to work with Streamlit.

# Define the clauses we want the LLM to look for
CLAUSES_TO_CHECK = [
    "Confidentiality", "Limitation of Liability", "Governing Law",
    "Termination for Cause", "Indemnification", "Intellectual Property",
    "Dispute Resolution", "Force Majeure"
]

def extract_text_from_pdf(pdf_file_bytes: bytes) -> str:
    """Extracts text from a PDF file's bytes."""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_file_bytes))
        text = "".join(page.extract_text() for page in pdf_reader.pages)
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
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
    
    **CRITICAL:** Ensure that any double quotes within the "justification" or "cited_text" values are properly escaped with a backslash (e.g., "he said \\"hello\\"").

    ---
    **CONTRACT TEXT:**
    ---
    {contract_text}
    """
    return prompt

def verify_clauses_with_llm(contract_text: str, api_key: str):
    """
    Uses a Large Language Model (Gemini) with an advanced prompt to analyze contract text.
    """
    try:
        genai.configure(api_key=api_key)
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
        st.error(f"LLM Error: Failed to decode JSON from the model's response. Raw response: {response.text}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during LLM verification: {e}")
        return None

# --- Streamlit User Interface ---

st.set_page_config(page_title="AI Contract Analyzer", layout="wide")

st.title("🤖 Agent B: AI-Powered Contract Analyzer")
st.markdown("Upload a contract PDF to have an AI paralegal analyze it for the presence of key legal clauses.")

# --- Sidebar for API Key and Inputs ---
with st.sidebar:
    st.header("Configuration")
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password")
    st.markdown("[Get an API key from Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    uploaded_file = st.file_uploader("Upload Contract PDF", type="pdf")
    
    analyze_button = st.button("Analyze Contract", type="primary", use_container_width=True)

# --- Main Content Area for Results ---
if analyze_button:
    if not gemini_api_key:
        st.warning("Please enter your Gemini API Key in the sidebar.")
    elif not uploaded_file:
        st.warning("Please upload a contract PDF in the sidebar.")
    else:
        with st.spinner('AI is analyzing the document... This may take a moment.'):
            pdf_bytes = uploaded_file.getvalue()
            contract_text = extract_text_from_pdf(pdf_bytes)
            
            if contract_text:
                results = verify_clauses_with_llm(contract_text, gemini_api_key)
                
                if results:
                    st.header("Analysis Summary")
                    if results["is_verified"]:
                        st.success(f"**Status: Contract Verified.** {results['summary']}")
                    else:
                        st.error(f"**Status: Verification Failed.** {results['summary']}")
                    
                    st.divider()

                    # Display detailed results
                    st.subheader("✅ Clauses Found")
                    if results["clauses_found"]:
                        for item in results["clauses_found"]:
                            with st.expander(f"**{item['clause']}**"):
                                st.markdown(f"**Justification:** {item['justification']}")
                                st.info(f"**Cited Text:** \"...{item['cited_text']}...\"")
                    else:
                        st.write("No required clauses were found.")

                    st.subheader("❌ Clauses Missing")
                    if results["clauses_missing"]:
                         for item in results["clauses_missing"]:
                            with st.expander(f"**{item['clause']}**"):
                                st.markdown(f"**Justification:** {item['justification']}")
                    else:
                        st.write("No clauses were missing.") '''
