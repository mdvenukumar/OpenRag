import streamlit as st
import os
import time
import google.generativeai as genai
import tempfile
from tavily import TavilyClient
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure Gemini API
API_KEY = "AIzaSyAmm7Dvr2Rr6DbNUo4bV5bCWDYWSU2k3Sg"
genai.configure(api_key=API_KEY)

# Configure Tavily API
TAVILY_API_KEY = "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"
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

def upload_to_gemini(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        uploaded_file = genai.upload_file(tmp_file_path, mime_type="application/pdf")
        return uploaded_file
    finally:
        os.unlink(tmp_file_path)

def wait_for_file_active(file):
    with st.spinner("Processing file..."):
        file_status = genai.get_file(file.name)
        while file_status.state.name == "PROCESSING":
            time.sleep(2)
            file_status = genai.get_file(file.name)
        if file_status.state.name != "ACTIVE":
            st.error(f"File {file.name} failed to process")
            return False
    return True

def generate_title_from_summary(model, summary):
    prompt = f"Given the following summary of a document, generate a concise and descriptive title (maximum 5 words):\n\n{summary}\n\nTitle:"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating title: {str(e)}")
        return "Untitled Document"

def tavily_search(query, max_retries=3):
    if not query.strip():
        return None

    for attempt in range(max_retries):
        try:
            logging.info(f"Attempting Tavily search (attempt {attempt + 1})")
            response = tavily_client.search(query=query, search_depth="advanced", include_images=False, include_answer=True, max_results=5)
            logging.info(f"Tavily search successful: {response}")
            return response
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error in Tavily search (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logging.error(f"Unexpected error in Tavily search: {str(e)}")
            return None

# Create the Gemini model
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
)

# Streamlit app
st.set_page_config(page_title="OpenRAG", page_icon="📚", layout="wide")

# Custom CSS for a more professional look
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stApp {
        background-color: #f0f2f6;
    }
    .st-bx {
        background-color: white;
        border-radius: 5px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .st-emotion-cache-10trblm {
        font-weight: bold;
        color: #1f618d;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📚 OpenRAG: PDF Chat with Related Articles")

# Main content and sidebar layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("PDF Upload and Chat")
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    if uploaded_file is not None:
        if 'gemini_file' not in st.session_state:
            with st.spinner("Uploading and processing file..."):
                st.session_state.gemini_file = upload_to_gemini(uploaded_file)
                
                if wait_for_file_active(st.session_state.gemini_file):
                    st.session_state.chat_session = model.start_chat(
                        history=[
                            {
                                "role": "user",
                                "parts": [st.session_state.gemini_file, "What is the main topic or subject of this PDF? Provide a brief summary in 2-3 sentences."],
                            },
                        ]
                    )
                    summary_response = st.session_state.chat_session.send_message("Provide the summary.")
                    st.session_state.pdf_summary = summary_response.text
                    st.session_state.chat_history = []

                    # Generate title and search for related articles
                    with st.spinner("Fetching related articles..."):
                        pdf_title = generate_title_from_summary(model, st.session_state.pdf_summary)
                        st.session_state.pdf_title = pdf_title
                        search_query = f"Articles related to: {pdf_title}"
                        st.session_state.search_results = tavily_search(search_query)

        st.success("PDF processed successfully!")
        with st.expander("PDF Summary", expanded=True):
            st.write(st.session_state.pdf_summary)
            if 'pdf_title' in st.session_state:
                st.write(f"**Generated Title:** {st.session_state.pdf_title}")

        # Chat container
        chat_container = st.container()

        # User input for questions
        user_question = st.chat_input("Ask a question about the PDF:")
        
        if user_question:
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            
            with st.spinner("Generating response..."):
                response = st.session_state.chat_session.send_message(user_question)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})

        # Display chat history
        with chat_container:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🤖"):
                    st.markdown(message["content"])

    else:
        st.info("Please upload a PDF file to start chatting.")

with col2:
    st.subheader("Related Articles")
    if 'search_results' in st.session_state:
        if st.session_state.search_results is not None:
            for result in st.session_state.search_results.get('results', []):
                with st.expander(f"**{result.get('title', 'Untitled')}**", expanded=False):
                    st.write(f"[Read More]({result.get('url', '#')})")
                    

            if st.session_state.search_results.get('answer'):
                st.subheader("AI-Generated Summary of Related Content")
                st.write(st.session_state.search_results['answer'])
        else:
            st.warning("Unable to fetch related articles. Please check the logs for more information.")
    else:
        st.info("Upload a PDF to see related articles.")

# Add a footer
st.markdown("---")
st.markdown("OpenRAG - Powered by Gemini and Tavily")