# app.py
import streamlit as st
import asyncio
from typing import List

# Import all the necessary functions from your powerful verifier
from verifier import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_image,
    verify_contract_clauses,
    generate_clause_suggestion,
    generate_plain_english_summary,
    answer_contract_question
)

# --- Page Configuration ---
st.set_page_config(
    page_title="De-Sign AI Contract Co-Pilot",
    layout="wide",
    page_icon="✍️"
)

# --- Initialize Session State ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "contract_text" not in st.session_state:
    st.session_state.contract_text = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Predefined Clauses ---
DEFAULT_CLAUSES_TO_CHECK = [
    "Indemnification", "Limitation of Liability", "Intellectual Property Rights",
    "Confidentiality", "Termination for Cause", "Governing Law & Jurisdiction",
    "Data Privacy & Security", "Force Majeure"
]

# --- UI Layout ---

st.title("✍️ De-Sign: AI Contract Co-Pilot")
st.markdown("An AI paralegal to perform high-risk analysis, suggest improvements, translate legalese, and answer questions about your contracts (`.pdf`, `.docx`, `.png`, `.jpeg`).")

# --- Sidebar for Configuration and Actions ---
with st.sidebar:
    st.header("Configuration")
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password", help="Your key is not stored.")
    st.markdown("[Get an API key from Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    uploaded_file = st.file_uploader(
        "Upload Contract Document",
        type=["pdf", "docx", "png", "jpeg", "jpg"]
    )

    st.subheader("Clause Selection")
    st.markdown("Predefined clauses will always be checked. Add more below!")
    
    # Display predefined clauses
    st.info(f"**Default Clauses:** {', '.join(DEFAULT_CLAUSES_TO_CHECK)}")

    # User input for additional clauses
    user_custom_clauses_str = st.text_area(
        "Additional Clauses to Verify (comma-separated)",
        value="",
        placeholder="e.g., Payment Terms, Warranty, Exclusivity"
    )
    
    analyze_button = st.button("Analyze Contract", type="primary", use_container_width=True)

    # Buttons for extra features appear after a successful analysis
    if st.session_state.analysis_results:
        st.divider()
        st.header("AI Co-Pilot Features")
        summarize_button = st.button("Summarize in Plain English", use_container_width=True)
        if summarize_button and st.session_state.contract_text:
            with st.spinner("AI is generating a plain English summary..."):
                summary = asyncio.run(generate_plain_english_summary(st.session_state.contract_text, gemini_api_key))
                st.session_state.summary = summary


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
        st.session_state.messages = []

        # Combine default and user-defined clauses
        all_clauses_to_check = list(DEFAULT_CLAUSES_TO_CHECK)
        if user_custom_clauses_str:
            custom_clauses = [c.strip() for c in user_custom_clauses_str.split(',') if c.strip()]
            all_clauses_to_check.extend(custom_clauses)
        
        # Remove duplicates and ensure a consistent order
        all_clauses_to_check = sorted(list(set(all_clauses_to_check)))

        if not all_clauses_to_check:
            st.warning("No clauses selected for verification. Please add some.")
            st.stop() # Stop execution if no clauses are specified

        with st.spinner('AI is analyzing the document... This may take a moment.'):
            file_bytes = uploaded_file.getvalue()
            content_type = uploaded_file.type
            
            text = ""
            if content_type == "application/pdf":
                text = extract_text_from_pdf(file_bytes)
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = extract_text_from_docx(file_bytes)
            else: # Images
                text = extract_text_from_image(file_bytes)

            st.session_state.contract_text = text
            
            if text:
                # Call the main analysis function with the dynamic list of clauses
                results = asyncio.run(verify_contract_clauses(file_bytes, content_type, gemini_api_key, all_clauses_to_check))
                st.session_state.analysis_results = results
            else:
                st.error("Could not extract text from the document.")

# --- Display Results ---

if st.session_state.analysis_results:
    results = st.session_state.analysis_results
    analysis = results.get("analysis", [])
    
    if st.session_state.summary:
        st.subheader("Plain English Summary")
        st.info(st.session_state.summary)

    st.header("Contract Risk Analysis")

    # Calculate percentages for overall metrics
    total_clauses = len(analysis)
    high_risk_clauses = [item for item in analysis if item.get("risk_level") == "High"]
    medium_risk_clauses = [item for item in analysis if item.get("risk_level") == "Medium"]

    if total_clauses > 0:
        high_risk_percentage = (len(high_risk_clauses) / total_clauses) * 100
        medium_risk_percentage = (len(medium_risk_clauses) / total_clauses) * 100
    else:
        high_risk_percentage = 0
        medium_risk_percentage = 0

    col1, col2 = st.columns(2)
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

    st.divider()

    # Display the detailed clause-by-clause analysis with risk percentages
    for item in analysis:
        risk_level = item.get("risk_level", "Low")
        confidence = item.get("confidence_score", 0.0)
        
        # Determine the risk percentage for a single clause
        if risk_level in ["High", "Medium"]:
            risk_percent = 100
        else:
            risk_percent = 0

        icon = "🚨" if risk_level == "High" else "⚠️" if risk_level == "Medium" else "✅"
        
        with st.expander(f"{icon} **{item['clause_name']}** - Risk Level: {risk_level}"):
            st.markdown(f"**Justification:** {item['justification']}")
            if item['is_present']:
                st.info(f"**Cited Text:** \"...{item['cited_text']}...\"")

            st.markdown(f"**Risk Percentage:** {risk_percent:.0f}%")
            st.progress(confidence, text=f"Confidence: {confidence:.0%}")
            
            if risk_level in ["High", "Medium"]:
                if st.button("Suggest Fix", key=f"suggest_{item['clause_name']}", use_container_width=True):
                    with st.spinner(f"AI is generating a suggestion for '{item['clause_name']}'..."):
                        suggestion = asyncio.run(
                            generate_clause_suggestion(
                                clause_name=item['clause_name'], 
                                risky_text=item['cited_text'],
                                api_key=gemini_api_key
                            )
                        )
                        st.subheader("AI-Generated Suggestion:")
                        st.text_area("", value=suggestion, height=200, key=f"suggestion_text_{item['clause_name']}")

    # --- Interactive Q&A Chat ---
    st.divider()
    st.header("💬 Ask a Question About This Contract")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is the penalty for late payment?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                response = asyncio.run(
                    answer_contract_question(
                        contract_text=st.session_state.contract_text,
                        user_question=prompt,
                        api_key=gemini_api_key
                    )
                )
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
