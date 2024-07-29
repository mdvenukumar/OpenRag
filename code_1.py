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
st.set_page_config(page_title="DocuExplore", page_icon="⭕", layout="wide")
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
    .title-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .title-container .title {
        font-size: 2rem;
        font-weight: bold;
        color: #1f618d;
    }
    .title-container .subtitle {
        font-size: 1.2rem;
        color: #555;
    }
    .product-hunt-badge {
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⭕ DocuExplore: From PDF to Insight, Explore the Extra", anchor=False)
# Title and Product Hunt badge
st.markdown("""
    <div class="title-container">
        <div>
            <div class="title">DocuExplore</div>
            <div class="subtitle">From PDF to Insight, Explore the Extra</div>
        </div>
        <div class="product-hunt-badge">
            <a href="https://www.producthunt.com/posts/docuexplore?embed=true&utm_source=badge-featured&utm_medium=badge&utm_souce=badge-docuexplore" target="_blank">
                <img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=474872&theme=dark" alt="DocuExplore - From PDF to Insight, Explore the Extra | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" />
            </a>
        </div>
    </div>
""", unsafe_allow_html=True)

# Main content and sidebar layout
col1, col2 = st.columns([2, 1])
@@ -180,29 +206,10 @@ def tavily_search(query, max_retries=3):
                with st.expander(f"**{result.get('title', 'Untitled')}**", expanded=False):
                    st.write(f"[Read More]({result.get('url', '#')})")


            if st.session_state.search_results.get('answer'):
                st.subheader("AI-Generated Summary of Related Content")
                st.write(st.session_state.search_results['answer'])
        else:
            st.warning("Unable to fetch related articles. Please check the logs for more information.")
    else:
        st.info("Upload a PDF to see related articles.")

st.markdown("""
    <style>
    .bottom-left {
        position: fixed;
        bottom: 0;
        left: 0;
        margin: 10px;
    }
    </style>
    <div class="bottom-left">
        <a href="https://www.producthunt.com/posts/docuexplore?embed=true&utm_source=badge-featured&utm_medium=badge&utm_souce=badge-docuexplore" target="_blank">
            <img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=474872&theme=dark" alt="DocuExplore - From PDF to Insight, Explore the Extra | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" />
        </a>
    </div>
""", unsafe_allow_html=True)

