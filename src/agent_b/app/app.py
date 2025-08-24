# app.py
import streamlit as st
import asyncio

# Import all the necessary functions from your powerful verifier
from verifier import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_image,
    verify_contract_clauses,
    generate_clause_suggestion,
    generate_plain_english_summary,
    answer_contract_question  # Import the new Q&A function
)

# --- Page Configuration ---
st.set_page_config(
    page_title="De-Sign AI Contract Co-Pilot",
    layout="wide",
    page_icon="✍️"
)

# --- Initialize Session State ---
# This is crucial for making the app interactive without losing data.
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "contract_text" not in st.session_state:
    st.session_state.contract_text = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "messages" not in st.session_state: # For the Q&A chat
    st.session_state.messages = []


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

        with st.spinner('AI is analyzing the document... This may take a moment.'):
            file_bytes = uploaded_file.getvalue()
            content_type = uploaded_file.type
            
            if content_type == "application/pdf":
                text = extract_text_from_pdf(file_bytes)
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = extract_text_from_docx(file_bytes)
            else: # Images
                text = extract_text_from_image(file_bytes)

            st.session_state.contract_text = text
            
            if text:
                # Call the main analysis function
                results = asyncio.run(verify_contract_clauses(file_bytes, content_type, gemini_api_key))
                st.session_state.analysis_results = results
            else:
                st.error("Could not extract text from the document.")

# --- Display Results ---

if st.session_state.analysis_results:
    results = st.session_state.analysis_results
    analysis = results.get("analysis", [])
    
    # Display the summary if it has been generated
    if st.session_state.summary:
        st.subheader("Plain English Summary")
        st.info(st.session_state.summary)

    st.header("Contract Risk Analysis")

    # Create columns for a dashboard-like view
    col1, col2 = st.columns(2)
    high_risk_clauses = [item for item in analysis if item.get("risk_level") == "High"]
    medium_risk_clauses = [item for item in analysis if item.get("risk_level") == "Medium"]
    with col1:
        st.metric("High-Risk Clauses", len(high_risk_clauses), delta_color="inverse")
    with col2:
        st.metric("Medium-Risk Clauses", len(medium_risk_clauses), delta_color="inverse")

    st.divider()

    # Display the detailed clause-by-clause analysis
    for item in analysis:
        risk_level = item.get("risk_level", "Low")
        icon = "🚨" if risk_level == "High" else "⚠️" if risk_level == "Medium" else "✅"
        
        with st.expander(f"{icon} **{item['clause_name']}** - Risk Level: {risk_level}"):
            st.markdown(f"**Justification:** {item['justification']}")
            if item['is_present']:
                st.info(f"**Cited Text:** \"...{item['cited_text']}...\"")
            st.progress(item['confidence_score'], text=f"Confidence: {item['confidence_score']:.0%}")
            
            # Add the "Suggest Fix" button for problematic clauses
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

    # --- NEW: Feature 1 - Interactive Q&A Chat ---
    st.divider()
    st.header("💬 Ask a Question About This Contract")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input for user's question
    if prompt := st.chat_input("What is the penalty for late payment?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
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
        
        # Add AI response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

