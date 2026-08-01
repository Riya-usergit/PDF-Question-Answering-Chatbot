import streamlit as pd_qa_streamlit
import requests
import os
import time

# Set page title and layout
pd_qa_streamlit.set_page_config(
    page_title="AI PDF QA Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API configuration
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

# Inject Custom CSS for Premium UI styling
pd_qa_streamlit.markdown("""
    <style>
        /* Import premium Outfit font */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }

        /* App-wide theme refinements */
        .reportview-container {
            background-color: #0F172A;
        }

        /* Title styling with elegant gradient */
        .title-gradient {
            background: linear-gradient(135deg, #a78bfa 0%, #f472b6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
            padding-top: 10px;
        }

        .subtitle-text {
            color: #94A3B8;
            font-size: 1.1rem;
            margin-bottom: 2rem;
            font-weight: 300;
        }

        /* Sidebar customized cards */
        .sidebar-section {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }

        .sidebar-header {
            color: #E2E8F0;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 5px;
        }

        /* Document list items */
        .doc-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }

        .doc-name {
            color: #CBD5E1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 180px;
        }

        /* Custom chat bubble design */
        .chat-bubble {
            padding: 16px 20px;
            border-radius: 16px;
            margin-bottom: 15px;
            max-width: 85%;
            line-height: 1.6;
            font-size: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        .user-bubble {
            background-color: #312E81;
            color: #F8FAFC;
            margin-left: auto;
            border-bottom-right-radius: 4px;
            border: 1px solid #4338CA;
        }

        .assistant-bubble {
            background-color: #1E293B;
            color: #F1F5F9;
            margin-right: auto;
            border-bottom-left-radius: 4px;
            border: 1px solid #334155;
        }

        /* Source citation badge pills */
        .citation-container {
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }

        .citation-badge {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            color: #FFFFFF !important;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Welcome card */
        .welcome-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .welcome-title {
            color: #F1F5F9;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .welcome-desc {
            color: #94A3B8;
            max-width: 600px;
            margin: 0 auto 20px auto;
            line-height: 1.5;
        }
    </style>
""", unsafe_allow_html=True)

# Helper function to query API documents
def get_uploaded_documents():
    try:
        response = requests.get(f"{BACKEND_URL}/documents")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        pd_qa_streamlit.sidebar.error(f"Could not connect to backend: {e}")
        return []

# Helper function to delete document
def delete_document(doc_id):
    try:
        res = requests.delete(f"{BACKEND_URL}/document/{doc_id}")
        return res.status_code == 200
    except Exception as e:
        pd_qa_streamlit.sidebar.error(f"Error deleting file: {e}")
        return False

# Helper function to get history
def get_chat_history():
    try:
        response = requests.get(f"{BACKEND_URL}/history")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

# Helper function to clear history
def clear_chat_history():
    try:
        res = requests.delete(f"{BACKEND_URL}/history")
        return res.status_code == 200
    except Exception:
        return False

# Header rendering
pd_qa_streamlit.markdown('<h1 class="title-gradient">AI PDF QA Chatbot</h1>', unsafe_allow_html=True)
pd_qa_streamlit.markdown('<p class="subtitle-text">Production-ready Retrieval-Augmented Generation (RAG) chatbot using FastAPI, Streamlit, and Gemini.</p>', unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
pd_qa_streamlit.sidebar.markdown('<div class="sidebar-header">📤 UPLOAD DOCUMENTS</div>', unsafe_allow_html=True)

# PDF Uploader
uploaded_files = pd_qa_streamlit.sidebar.file_uploader(
    "Choose PDF files to analyze",
    type=["pdf"],
    accept_multiple_files=True,
    help="Upload multi-page PDFs to index in FAISS"
)

# Process uploads
if uploaded_files:
    for file in uploaded_files:
        # Check if already processed to avoid repeating on re-render
        session_upload_key = f"uploaded_{file.name}"
        if session_upload_key not in pd_qa_streamlit.session_state:
            with pd_qa_streamlit.spinner(f"Uploading & indexing '{file.name}'..."):
                try:
                    files = {"file": (file.name, file.getvalue(), "application/pdf")}
                    response = requests.post(f"{BACKEND_URL}/upload", files=files)
                    if response.status_code == 201:
                        pd_qa_streamlit.session_state[session_upload_key] = True
                        pd_qa_streamlit.sidebar.success(f"Indexed '{file.name}'!")
                        time.sleep(1)
                        pd_qa_streamlit.rerun()
                    else:
                        detail = response.json().get("detail", "Error processing file.")
                        pd_qa_streamlit.sidebar.error(f"Failed to process '{file.name}': {detail}")
                except Exception as e:
                    pd_qa_streamlit.sidebar.error(f"Error communicating with server: {e}")

# Display Documents List
pd_qa_streamlit.sidebar.markdown('<div class="sidebar-header">📚 CURRENTLY INDEXED</div>', unsafe_allow_html=True)
docs = get_uploaded_documents()

if docs:
    for doc in docs:
        col1, col2 = pd_qa_streamlit.sidebar.columns([6, 1])
        with col1:
            pd_qa_streamlit.markdown(f"""
                <div class="doc-item">
                    <span class="doc-name" title="{doc['filename']}">{doc['filename']}</span>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            # We use an unique key for each delete button
            if pd_qa_streamlit.button("🗑️", key=f"del_{doc['id']}", help=f"Delete '{doc['filename']}'"):
                with pd_qa_streamlit.spinner("Deleting..."):
                    if delete_document(doc['id']):
                        pd_qa_streamlit.sidebar.success(f"Deleted '{doc['filename']}'")
                        # Clear upload session flag if present
                        pd_qa_streamlit.session_state.pop(f"uploaded_{doc['filename']}", None)
                        time.sleep(1)
                        pd_qa_streamlit.rerun()
                    else:
                        pd_qa_streamlit.sidebar.error("Failed to delete.")
else:
    pd_qa_streamlit.sidebar.info("No documents uploaded yet. Please upload a PDF to get started.")

# Sidebar Settings
pd_qa_streamlit.sidebar.markdown('<div class="sidebar-header">⚙️ CONTROLS</div>', unsafe_allow_html=True)
if pd_qa_streamlit.sidebar.button("🧹 Clear Chat History", use_container_width=True):
    if clear_chat_history():
        pd_qa_streamlit.sidebar.success("Chat history cleared!")
        time.sleep(1)
        pd_qa_streamlit.rerun()
    else:
        pd_qa_streamlit.sidebar.error("Failed to clear chat history.")


# ----------------- MAIN CHAT INTERFACE -----------------

# Fetch history on render
history = get_chat_history()

# If history is empty and no documents uploaded, render welcome card
if not history:
    pd_qa_streamlit.markdown("""
        <div class="welcome-card">
            <div class="welcome-title">Welcome to the AI PDF Chatbot! 🚀</div>
            <p class="welcome-desc">
                This app uses Retrieval-Augmented Generation (RAG) to answer questions directly from your PDFs. 
                Answers are grounded strictly in the document content to avoid hallucinations.
            </p>
            <div style="font-size: 0.95rem; color: #64748B;">
                👈 Start by uploading your PDF files in the sidebar. Once indexed, type your question below!
            </div>
        </div>
    """, unsafe_allow_html=True)

# Render Chat History
for message in history:
    # Render User bubble
    pd_qa_streamlit.markdown(
        f'<div class="chat-bubble user-bubble"><b>You:</b><br>{message["question"]}</div>',
        unsafe_allow_html=True
    )
    
    # Render Assistant bubble with references
    sources_html = ""
    if message.get("sources"):
        badges = []
        for src in message["sources"]:
            badges.append(f'<span class="citation-badge">📄 {src["filename"]} (Pg {src["page"]})</span>')
        sources_html = f'<div class="citation-container">{" ".join(badges)}</div>'

    pd_qa_streamlit.markdown(
        f'<div class="chat-bubble assistant-bubble"><b>Assistant:</b><br>{message["answer"]}{sources_html}</div>',
        unsafe_allow_html=True
    )

# Accept User Question
user_query = pd_qa_streamlit.chat_input("Ask a question about the uploaded documents...")

if user_query:
    # 1. Render user question instantly
    pd_qa_streamlit.markdown(
        f'<div class="chat-bubble user-bubble"><b>You:</b><br>{user_query}</div>',
        unsafe_allow_html=True
    )
    
    # 2. Query backend and render assistant response with spinner
    with pd_qa_streamlit.spinner("Analyzing documents & generating answer..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/ask",
                json={"question": user_query}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                sources = data["sources"]
                
                # Format sources HTML
                sources_html = ""
                if sources:
                    badges = []
                    for src in sources:
                        badges.append(f'<span class="citation-badge">📄 {src["filename"]} (Pg {src["page"]})</span>')
                    sources_html = f'<div class="citation-container">{" ".join(badges)}</div>'
                
                # Render response
                pd_qa_streamlit.markdown(
                    f'<div class="chat-bubble assistant-bubble"><b>Assistant:</b><br>{answer}{sources_html}</div>',
                    unsafe_allow_html=True
                )
                
                # Refresh page to maintain scroll positioning and sync session storage state
                pd_qa_streamlit.rerun()
                
            else:
                error_msg = response.json().get("detail", "Unknown server error.")
                pd_qa_streamlit.error(f"Backend Server Error: {error_msg}")
        except Exception as e:
            pd_qa_streamlit.error(f"Error querying backend API: {e}")
