import streamlit as st
import requests
import os
import time

# Set up browser page options
st.set_page_config(
    page_title="AI PDF QA Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Backend API server URL connection
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

# Render header text
st.title("🤖 AI PDF Question Answering Chatbot")
st.write("Upload PDF documents and ask natural language questions. All answers are grounded strictly in the PDF text using RAG (Retrieval-Augmented Generation).")

# --- Helper Functions to Talk to Backend API ---

def get_uploaded_documents():
    """Queries the backend to get a list of all indexed PDF documents."""
    try:
        response = requests.get(f"{BACKEND_URL}/documents")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.sidebar.error(f"Cannot connect to backend server: {e}")
    return []

def upload_document(file_name, file_bytes):
    """Sends a PDF file to the backend to be uploaded and indexed."""
    try:
        files = {"file": (file_name, file_bytes, "application/pdf")}
        response = requests.post(f"{BACKEND_URL}/upload", files=files)
        return response.status_code == 201
    except Exception as e:
        st.sidebar.error(f"File upload failed: {e}")
    return False

def delete_document(doc_id):
    """Asks the backend to delete a PDF and remove its chunks from FAISS."""
    try:
        response = requests.delete(f"{BACKEND_URL}/document/{doc_id}")
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Document deletion failed: {e}")
    return False

def get_chat_history():
    """Fetches past QA interactions from the SQLite database."""
    try:
        response = requests.get(f"{BACKEND_URL}/history")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

def clear_chat_history():
    """Tells the backend to wipe the SQLite conversation log."""
    try:
        response = requests.delete(f"{BACKEND_URL}/history")
        return response.status_code == 200
    except Exception:
        pass
    return False


# ----------------- SIDEBAR UI: FILE MANAGEMENT -----------------

st.sidebar.header("📤 Document Manager")

# Streamlit file upload widget
uploaded_files = st.sidebar.file_uploader(
    "Choose PDF files to upload:",
    type=["pdf"],
    accept_multiple_files=True
)

# If the user dragged/selected new files, send them to the backend API
if uploaded_files:
    for file in uploaded_files:
        session_key = f"uploaded_{file.name}"
        if session_key not in st.session_state:
            with st.sidebar.spinner(f"Uploading & indexing '{file.name}'..."):
                if upload_document(file.name, file.getvalue()):
                    st.session_state[session_key] = True
                    st.sidebar.success(f"Indexed '{file.name}' successfully!")
                    time.sleep(1)
                    st.rerun()

st.sidebar.write("---")
st.sidebar.header("📚 Currently Indexed PDFs")

# Retrieve the list of active documents from backend and render them
docs = get_uploaded_documents()
if docs:
    for doc in docs:
        col1, col2 = st.sidebar.columns([5, 1])
        with col1:
            st.text(doc["filename"])
        with col2:
            # Custom trash button to trigger deletion
            if st.button("🗑️", key=f"del_{doc['id']}", help="Remove this PDF from vector store"):
                with st.spinner("Deleting document..."):
                    if delete_document(doc['id']):
                        st.sidebar.success("Deleted!")
                        st.session_state.pop(f"uploaded_{doc['filename']}", None)
                        time.sleep(1)
                        st.rerun()
else:
    st.sidebar.info("No documents uploaded yet.")

st.sidebar.write("---")
st.sidebar.header("⚙️ Chat Actions")
if st.sidebar.button("🧹 Clear Chat History", use_container_width=True):
    if clear_chat_history():
        st.sidebar.success("Chat history cleared!")
        time.sleep(1)
        st.rerun()


# ----------------- MAIN UI: CHAT WINDOW -----------------

# Fetch past conversation messages
chat_history = get_chat_history()

# Render a helpful welcome panel if there's no chat history yet
if not chat_history:
    st.info("👈 Upload PDF documents in the sidebar, then ask a question below to start chatting!")

# Render conversation history using Streamlit's native chat UI blocks
for message in chat_history:
    with st.chat_message("user"):
        st.write(message["question"])
    
    with st.chat_message("assistant"):
        st.write(message["answer"])
        
        # Display source citations underneath the answer
        if message.get("sources"):
            st.write("**Sources:**")
            badges = [f"`📄 {s['filename']} (Pg {s['page']})`" for s in message["sources"]]
            st.markdown(" ".join(badges))

# Accept user input from the chat box
user_query = st.chat_input("Ask a question about the uploaded PDFs...")

if user_query:
    # 1. Render user message instantly in the UI
    with st.chat_message("user"):
        st.write(user_query)
        
    # 2. Send query to API server with a progress spinner
    with st.spinner("Analyzing documents & generating answer..."):
        try:
            response = requests.post(f"{BACKEND_URL}/ask", json={"question": user_query})
            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                sources = data["sources"]
                
                # Render assistant reply
                with st.chat_message("assistant"):
                    st.write(answer)
                    
                    # If sources exist, render page badges
                    if sources:
                        st.write("**Sources:**")
                        badges = [f"`📄 {s['filename']} (Pg {s['page']})`" for s in sources]
                        st.markdown(" ".join(badges))
                
                # Refresh page to maintain view state and scroll positions
                st.rerun()
            else:
                error_msg = response.json().get("detail", "Unknown server error.")
                st.error(f"Backend Server Error: {error_msg}")
        except Exception as e:
            st.error(f"Failed to communicate with API server: {e}")
