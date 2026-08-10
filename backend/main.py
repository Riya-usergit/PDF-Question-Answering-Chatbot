import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.config.settings import settings
from backend.database import models as db_models
from backend.services.storage_service import storage_service
from backend.rag.pdf_processor import process_pdf
from backend.rag.vector_store import (
    add_chunks_to_vector_store,
    delete_document_chunks_from_vector_store,
    search_similarity
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# Initialize logging to show server information in the console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Schemas for Request & Response Validation ---

class DocumentResponse(BaseModel):
    id: int
    filename: str
    s3_url: str
    upload_time: str

class AskRequest(BaseModel):
    question: str

class SourceCitation(BaseModel):
    filename: str
    page: int

class AskResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]

class ChatHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: str
    sources: List[SourceCitation]

# --- FastAPI Initialization & Lifecycle ---

# We define the LLM client globally
llm = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan runs database setup and initializes 
    the Gemini model once when the server boots.
    """
    global llm
    logger.info("Starting up backend services...")
    
    # 1. Setup SQLite Database Tables
    try:
        db_models.init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e
        
    # 2. Setup Google Gemini 3.5 Flash Client using LangChain
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0  # Temperature=0 forces deterministic, factual answers
        )
        logger.info("Successfully loaded Google Gemini client.")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini. Verify GEMINI_API_KEY in .env. Details: {e}")
        
    yield
    logger.info("Shutting down backend services...")

# Creating the FastAPI App Instance
app = FastAPI(
    title="AI PDF QA Chatbot",
    description="A simplified single-file REST API backend for beginner GenAI engineers.",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) 
# Allows our Streamlit frontend on port 8501 to talk to port 8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/")
async def health_check():
    """Simple API health diagnostic check."""
    return {
        "status": "healthy",
        "model": "gemini-3.5-flash",
        "description": "API is active and listening."
    }

@app.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Extracts PDF text chunks, creates vector embeddings, 
    saves the file, and registers metadata.
    """
    # 1. Validate file extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF file is empty."
        )

    filename = file.filename

    # Overwrite check: If filename exists, delete old file & FAISS chunks to avoid search duplicates
    existing_doc = db_models.get_document_by_filename(filename)
    if existing_doc:
        logger.info(f"Document '{filename}' already exists. Cleaning old index entries...")
        try:
            storage_service.delete_file(filename)
            delete_document_chunks_from_vector_store(filename)
            db_models.delete_document(existing_doc["id"])
        except Exception as e:
            logger.warning(f"Error during overwrite cleanup for '{filename}': {e}")

    try:
        # 2. Upload file (local folder or Supabase storage)
        storage_url = storage_service.upload_file(content, filename)

        # 3. Parse PDF page-by-page and chunk it
        chunks = process_pdf(content, filename)
        
        # 4. Generate embeddings and save to FAISS Vector Database
        if chunks:
            add_chunks_to_vector_store(chunks)
        else:
            logger.warning("No text extracted from PDF. Vector database was not updated.")

        # 5. Insert metadata into SQLite Database
        doc_id = db_models.add_document(filename, storage_url)
        doc_record = db_models.get_document_by_id(doc_id)
        
        return DocumentResponse(
            id=doc_record["id"],
            filename=doc_record["filename"],
            s3_url=doc_record["s3_url"],
            upload_time=doc_record["upload_time"]
        )
        
    except Exception as e:
        logger.error(f"Error processing upload for '{filename}': {e}")
        # Clean up database/vector storage logs if processing failed midway
        try:
            storage_service.delete_file(filename)
            delete_document_chunks_from_vector_store(filename)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while uploading and indexing the PDF: {str(e)}"
        )

@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """Returns a list of all indexed PDF documents."""
    docs = db_models.get_documents()
    return [
        DocumentResponse(
            id=doc["id"],
            filename=doc["filename"],
            s3_url=doc["s3_url"],
            upload_time=doc["upload_time"]
        ) for doc in docs
    ]

@app.delete("/document/{id}")
async def delete_document(id: int):
    """Deletes a document from SQLite database, storage, and FAISS index."""
    doc = db_models.get_document_by_id(id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    filename = doc["filename"]
    try:
        # 1. Delete file from storage
        storage_service.delete_file(filename)

        # 2. Wipe chunks from FAISS vector store
        delete_document_chunks_from_vector_store(filename)

        # 3. Wipe row from SQLite
        db_models.delete_document(id)
        return {"detail": f"Document '{filename}' deleted successfully."}
        
    except Exception as e:
        logger.error(f"Error deleting document '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Retrieves matching document context blocks from FAISS similarity search,
    compiles a system prompt, and calls Google Gemini API.
    """
    global llm
    if not llm:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini LLM client is not initialized. Check your GEMINI_API_KEY."
        )

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # Prompt user to upload files first if document database is empty
    if not db_models.get_documents():
        return AskResponse(
            answer="Please upload one or more PDF documents in the sidebar first.",
            sources=[]
        )

    try:
        # 1. Similarity Search in FAISS (Retrieves top 5 matching text chunks)
        retrieved_docs = search_similarity(question, k=5)
        if not retrieved_docs:
            return AskResponse(
                answer="I couldn't find any relevant text segments matching your query.",
                sources=[]
            )

        # 2. Build contextual context text blocks and citation list
        context_parts = []
        sources_list = []
        
        for doc in retrieved_docs:
            src_filename = doc.metadata.get("source", "Unknown Document")
            src_page = doc.metadata.get("page", 0)
            
            context_parts.append(
                f"Source: {src_filename} | Page: {src_page}\n"
                f"Content: {doc.page_content.strip()}"
            )
            
            citation = SourceCitation(filename=src_filename, page=src_page)
            if citation not in sources_list:
                sources_list.append(citation)

        context_string = "\n\n---\n\n".join(context_parts)

        # 3. Create context-aware System Prompt instructions
        system_instruction = (
            "You are a precise GenAI assistant. Answer the user's question using ONLY the provided context blocks below.\n"
            "If the context does not contain the answer, say exactly: 'I cannot find the answer in the uploaded documents.'\n"
            "Do NOT use external knowledge. Be factual, objective, and brief.\n\n"
            f"Context blocks:\n{context_string}"
        )

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=question)
        ]

        # 4. Generate answer from Gemini LLM
        response = llm.invoke(messages)
        
        # Safely parse response content. (Gemini response.content can be returned 
        # as a list of dict blocks rather than a plain string, so we extract text parts recursively)
        if isinstance(response.content, list):
            parts = []
            for block in response.content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif hasattr(block, "get") and block.get("text"):
                    parts.append(block.get("text"))
            answer = "".join(parts).strip()
        else:
            answer = str(response.content).strip()

        if not answer:
            answer = "I cannot find the answer in the uploaded documents."

        # If LLM failed to find answer, omit citations
        if "cannot find the answer" in answer.lower():
            sources_list = []

        # 5. Log transaction into chat history in SQLite
        sources_dict_list = [{"filename": s.filename, "page": s.page} for s in sources_list]
        db_models.add_chat_history(question, answer, sources_dict_list)

        return AskResponse(answer=answer, sources=sources_list)

    except Exception as e:
        logger.error(f"Error generating answer for '{question}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the answer: {str(e)}"
        )

@app.get("/history", response_model=List[ChatHistoryItem])
async def get_history():
    """Retrieves chat logs, mapping SQLite dictionary rows back to schemas."""
    history = db_models.get_chat_history()
    return [
        ChatHistoryItem(
            id=item["id"],
            question=item["question"],
            answer=item["answer"],
            timestamp=item["timestamp"],
            sources=[SourceCitation(filename=s["filename"], page=s["page"]) for s in item["sources"]]
        ) for item in history
    ]

@app.delete("/history")
async def clear_history():
    """Wipes the conversation logs from SQLite."""
    db_models.clear_chat_history()
    return {"detail": "Chat history cleared successfully."}
