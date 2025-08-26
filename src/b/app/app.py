# app.py
import streamlit as st
import json
from typing import List, Dict, Any
import pandas as pd
import plotly.express as px
import io # Import io for file handling
import requests # Import requests to make API calls to your FastAPI backend

# --- Page Configuration ---
st.set_page_config(
    page_title="De-Sign AI Contract Co-Pilot",
    layout="wide",
    page_icon="✍️"
)

# --- FastAPI Backend URL ---
# IMPORTANT: Ensure your FastAPI backend is running at this address.
FASTAPI_BASE_URL = "http://127.0.0.1:8000/api/v1"

# --- Initialize Session State ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "contract_text" not in st.session_state:
    st.session_state.contract_text = None
if "summary" not in st.session_state: # Plain English summary, distinct from executive risk summary
    st.session_state.summary = None
if "executive_risk_summary" not in st.session_state: # New: Executive risk summary
    st.session_state.executive_risk_summary = None
if "key_terms_and_obligations" not in st.session_state: # New: Key terms
    st.session_state.key_terms_and_obligations = None
# FIX: Re-initialize 'messages' for the Q&A chat feature
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- Predefined Clauses ---
DEFAULT_CLAUSES_TO_CHECK = [
    "Indemnification", "Limitation of Liability", "Intellectual Property Rights",
    "Confidentiality", "Termination for Cause", "Governing Law & Jurisdiction",
    "Data Privacy & Security", "Force Majeure", "Payment Terms", "Warranties" # Added more common clauses
]

# --- UI Layout ---

st.title("✍️ De-Sign: AI Contract Co-Pilot (Streamlit Frontend)")
st.markdown("An AI paralegal to perform high-risk analysis, suggest improvements, translate legalese, and answer questions about your contracts (`.pdf`, `.docx`, `.png`, `.jpeg`).")

# --- Sidebar for Configuration and Actions ---
with st.sidebar:
    st.header("Configuration")
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password", help="Your key is not stored.")
    st.markdown("[Get a Gemini API key from Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    uploaded_file = st.file_uploader(
        "Upload Contract Document",
        type=["pdf", "docx", "png", "jpeg", "jpg"]
    )

    st.subheader("Company & Context Settings")
    company_risk_appetite = st.select_slider(
        "Your Company's Risk Appetite",
        options=["Conservative", "Moderate", "Aggressive"],
        value="Moderate",
        help="How risk-averse is your company? This influences AI's assessment."
    )
    counterparty_type = st.selectbox(
        "Counterparty Type",
        options=["Large Enterprise Client", "Small Startup Vendor", "Strategic Partner", "Government Entity", "Other"],
        index=0,
        help="Who are you contracting with? Provides context for risk assessment."
    )
    selected_regulations = st.multiselect(
        "Relevant Regulations to Comply With",
        options=["GDPR", "CCPA", "HIPAA", "SOX", "Local Data Protection Laws", "None"],
        default=["None"],
        help="Select any external regulations the contract must adhere to."
    )
    
    st.subheader("Policy Documents & Text Input")
    uploaded_policy_files = st.file_uploader(
        "Upload Policy Documents (PDF, DOCX, IMG)",
        type=["pdf", "docx", "png", "jpeg", "jpg"],
        accept_multiple_files=True,
        help="Upload internal policy documents or relevant government guidelines. AI will read these for compliance checks."
    )
    sidebar_policy_text = st.text_area(
        "Or enter Policy Text directly here",
        value="",
        height=150,
        placeholder="E.g., 'Our internal policy states that all data must be hosted in AWS EU regions.'",
        help="Type specific policy text or rules for the AI to consider."
    )

    st.subheader("Clause Playbook Rules")
    playbook_rules_str = st.text_area(
        "Your Company's Clause Playbook (Clause: Preferred Text)",
        value="""Indemnification: Each party indemnifies the other for direct damages only, capped at 2x annual fees.\nConfidentiality: Data must be encrypted at rest and in transit, and stored within the EU, with a breach notification period of 48 hours.""",
        height=150,
        help="Enter your company's preferred language for clauses (e.g., 'Clause Name: Preferred Text'). AI will flag deviations."
    )
    
    st.subheader("Dynamic Clause Selection")
    st.markdown("Predefined clauses will always be checked. Add more below!")
    
    # Display predefined clauses
    st.info(f"**Default Clauses:** {', '.join(DEFAULT_CLAUSES_TO_CHECK)}")

    # User input for additional clauses
    user_custom_clauses_str = st.text_area(
        "Additional Clauses to Verify (comma-separated)",
        value="",
        placeholder="e.g., Data Security Measures, Audit Rights, Service Credits"
    )
    
    analyze_button = st.button("Analyze Contract", type="primary", use_container_width=True)

    # Buttons for extra features appear after a successful analysis
    if st.session_state.analysis_results:
        st.divider()
        st.header("AI Co-Pilot Tools")
        
        # Plain English Summary button
        if st.button("Generate Plain English Summary", use_container_width=True, help="A simple summary of the contract for non-legal teams."):
            if st.session_state.contract_text:
                with st.spinner("AI is generating a plain English summary..."):
                    try:
                        response = requests.post(
                            f"{FASTAPI_BASE_URL}/summarize",
                            headers={"X-API-Key": gemini_api_key},
                            json={"contract_text": st.session_state.contract_text}
                        )
                        response.raise_for_status() # Raise an exception for HTTP errors
                        st.session_state.summary = response.json().get("summary")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error calling summarize API: {e}")
            else:
                st.warning("Please analyze a contract first to generate a summary.")


# --- Main Logic ---

if analyze_button:
    if not gemini_api_key:
        st.warning("Please enter your Gemini API Key in the sidebar.")
    elif not uploaded_file:
        st.warning("Please upload a contract document in the sidebar.")
    else:
        # Reset all previous results for a new analysis
        st.session_state.analysis_results = None
        st.session_state.contract_text = None
        st.session_state.summary = None
        st.session_state.executive_risk_summary = None
        st.session_state.key_terms_and_obligations = None
        # FIX: Ensure messages are reset here for a fresh start
        st.session_state.messages = []

        # --- Prepare data for FastAPI call ---
        form_data = {
            "company_risk_appetite": company_risk_appetite,
            "counterparty_type": counterparty_type,
            "selected_regulations": ",".join([reg for reg in selected_regulations if reg != "None"]),
            "playbook_rules_str": playbook_rules_str,
            "user_custom_clauses_str": user_custom_clauses_str,
            "sidebar_policy_text": sidebar_policy_text,
        }
        
        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        
        # Add policy files to the 'files' dictionary for multipart/form-data
        if uploaded_policy_files:
            for i, policy_file in enumerate(uploaded_policy_files):
                # FastAPI expects specific naming for List[UploadFile] when sent via FormData
                # Using 'policy_files' as the key is correct for FastAPI's List[UploadFile]
                files[f'policy_files'] = (policy_file.name, policy_file.getvalue(), policy_file.type) 
        
        with st.spinner('AI is performing a deep contract analysis... This may take a moment.'):
            try:
                # Use requests to send a POST request to your FastAPI backend
                response = requests.post(
                    f"{FASTAPI_BASE_URL}/verify",
                    headers={
                        "X-API-Key": gemini_api_key,
                    },
                    data=form_data, # Use 'data' for form fields
                    files=files # Use 'files' for file uploads
                )
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                
                results = response.json()
                
                # Store all results in session state
                st.session_state.analysis_results = {"analysis": results.get("analysis", [])}
                st.session_state.executive_risk_summary = results.get("executive_summary", "No executive summary generated.")
                st.session_state.key_terms_and_obligations = results.get("key_terms_and_obligations", {})
                st.session_state.contract_text = results.get("contract_text", "") # Store full text for Q&A

            except requests.exceptions.HTTPError as e:
                st.error(f"API Error: {e.response.status_code} - {e.response.text}")
            except requests.exceptions.ConnectionError:
                st.error(f"Connection Error: Could not connect to FastAPI backend at {FASTAPI_BASE_URL}. Is it running?")
            except requests.exceptions.RequestException as e:
                st.error(f"An unexpected error occurred: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred during Streamlit processing: {e}")


# --- Display Results ---

if st.session_state.analysis_results and st.session_state.analysis_results.get("analysis"):
    analysis = st.session_state.analysis_results["analysis"]
    
    st.header("Executive Summary of Contract Risks 📈")
    if st.session_state.executive_risk_summary:
        st.info(st.session_state.executive_risk_summary)
    
    # Calculate overall numerical risk score
    total_numerical_score = sum(item.get('numerical_risk_score', 0) for item in analysis)
    max_possible_score = len(analysis) * 10 # Assuming max score of 10 per clause
    overall_contract_risk_percentage = (total_numerical_score / max_possible_score) * 100 if max_possible_score > 0 else 0

    st.subheader("Overall Contract Health")
    st.metric(
        "Overall Risk Score",
        f"{overall_contract_risk_percentage:.1f}%",
        help="Aggregated risk across all analyzed clauses, adjusted for company profile."
    )
    
    st.divider()

    st.header("Key Contract Terms & Obligations 📝")
    if st.session_state.key_terms_and_obligations:
        # Create a list of tuples for DataFrame, handling potential dict values
        key_terms_data = []
        for term, value in st.session_state.key_terms_and_obligations.items():
            if isinstance(value, list):
                key_terms_data.append((term, ", ".join(value)))
            elif isinstance(value, dict):
                key_terms_data.append((term, json.dumps(value))) # Convert dict to string
            else:
                key_terms_data.append((term, value))
        
        key_terms_df = pd.DataFrame(key_terms_data, columns=["Term", "Value"])
        st.table(key_terms_df)
    else:
        st.warning("Could not extract key terms and obligations.")

    if st.session_state.summary:
        st.header("Plain English Summary (for Business Teams) 📖")
        st.write(st.session_state.summary)
        st.divider()

    st.header("Detailed Clause Analysis & Risk Breakdown")

    # Calculate and display overall metrics (High/Medium risk percentages)
    total_clauses = len(analysis)
    high_risk_clauses = [item for item in analysis if item.get("risk_level") == "High"]
    medium_risk_clauses = [item for item in analysis if item.get("risk_level") == "Medium"]
    low_risk_clauses = [item for item in analysis if item.get("risk_level") == "Low"]

    if total_clauses > 0:
        high_risk_percentage = (len(high_risk_clauses) / total_clauses) * 100
        medium_risk_percentage = (len(medium_risk_clauses) / total_clauses) * 100
        low_risk_percentage = (len(low_risk_clauses) / total_clauses) * 100
    else:
        high_risk_percentage = 0
        medium_risk_percentage = 0
        low_risk_percentage = 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "High-Risk Clauses",
            f"{len(high_risk_clauses)} ({high_risk_percentage:.1f}%)",
            delta_color="inverse"
        )
    with col2:
        st.metric(
            "Medium-Risk Clauses",
            f"{len(medium_risk_clauses)} ({medium_risk_percentage:.1f}%)",
            delta_color="inverse"
        )
    with col3:
        st.metric(
            "Low-Risk Clauses",
            f"{len(low_risk_clauses)} ({low_risk_percentage:.1f}%)",
            delta_color="normal"
        )
    
    st.markdown("---")

    # --- Visualized Risk Distribution ---
    st.subheader("Risk Level Distribution")
    risk_data = pd.DataFrame({
        'Risk Level': ['High', 'Medium', 'Low'],
        'Count': [len(high_risk_clauses), len(medium_risk_clauses), len(low_risk_clauses)],
        'Percentage': [high_risk_percentage, medium_risk_percentage, low_risk_percentage]
    })
    fig = px.bar(risk_data, x='Risk Level', y='Count', color='Risk Level',
                 title='Distribution of Contract Clause Risk Levels',
                 labels={'Count': 'Number of Clauses'},
                 color_discrete_map={'High': 'red', 'Medium': 'orange', 'Low': 'green'},
                 text='Percentage')
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(yaxis_title='Number of Clauses', xaxis_title='Risk Level')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Display the detailed clause-by-clause analysis with risk percentages
    for item in analysis:
        risk_level = item.get("risk_level", "Low")
        confidence = item.get("confidence_score", 0.0)
        numerical_risk_score = item.get("numerical_risk_score", 0)
        
        # Determine the risk percentage for a single clause
        # This is a simplification; a true "clause risk percentage" would be more nuanced
        if risk_level == "High":
            risk_percent = 100
        elif risk_level == "Medium":
            risk_percent = 50
        else:
            risk_percent = 0

        icon = "🚨" if risk_level == "High" else "⚠️" if risk_level == "Medium" else "✅"
        
        with st.expander(f"{icon} **{item['clause_name']}** - Risk Level: {risk_level} (Score: {numerical_risk_score}/10)"):
            st.markdown(f"**Justification:** {item['justification']}")
            if item['is_present']:
                st.info(f"**Cited Text:** \"...{item['cited_text']}...\"")

            st.markdown(f"**Clause Risk Percentage:** {risk_percent:.0f}%")
            st.progress(confidence, text=f"AI Confidence: {confidence:.0%}")
            
            if risk_level in ["High", "Medium"] and st.session_state.contract_text:
                if st.button(f"Suggest Fix for {item['clause_name']}", key=f"suggest_{item['clause_name']}", use_container_width=True):
                    with st.spinner(f"AI is generating a suggestion for '{item['clause_name']}'..."):
                        # Provide relevant context for better suggestion
                        suggestion_context = f"""
                        Company Risk Appetite: {company_risk_appetite},
                        Counterparty Type: {counterparty_type},
                        Relevant Regulations: {', '.join(selected_regulations)},
                        Playbook Rules: {playbook_rules_str},
                        Additional Policies: {sidebar_policy_text}
                        """
                        try:
                            response = requests.post(
                                f"{FASTAPI_BASE_URL}/suggest-clause",
                                headers={"X-API-Key": gemini_api_key},
                                json={
                                    "clause_name": item['clause_name'],
                                    "risky_text": item['cited_text'],
                                    "context": suggestion_context
                                }
                            )
                            response.raise_for_status()
                            suggestion = response.json().get("suggestion")
                            st.subheader("AI-Generated Suggestion:")
                            st.text_area("", value=suggestion, height=200, key=f"suggestion_text_{item['clause_name']}")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Error calling suggest-clause API: {e}")

    # --- Exportable Analysis Report ---
    st.divider()
    st.header("Export Analysis Report 📥")
    
    # Prepare data for download
    download_data = {
        "overall_risk_score_percentage": f"{overall_contract_risk_percentage:.1f}%",
        "executive_summary": st.session_state.executive_risk_summary,
        "key_terms_and_obligations": st.session_state.key_terms_and_obligations,
        "detailed_clause_analysis": analysis
    }
    
    # Convert to JSON string for download
    json_export = json.dumps(download_data, indent=4)
    st.download_button(
        label="Download Full Analysis as JSON",
        data=json_export,
        file_name="de_sign_analysis_report.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Option to download raw contract text
    if st.session_state.contract_text:
        st.download_button(
            label="Download Original Contract Text",
            data=st.session_state.contract_text,
            file_name="original_contract_text.txt",
            mime="text/plain",
            use_container_width=True
        )


   

    

elif analyze_button: # If analyze button clicked but no results (e.g., text extraction failed)
    st.error("Failed to perform analysis. Please check your API key and document format.")

