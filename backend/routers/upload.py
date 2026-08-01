import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List
from backend.models.schemas import DocumentResponse
from backend.services.storage_service import storage_service
from backend.database import models as db_models
from backend.rag.pdf_processor import process_pdf
from backend.rag.vector_store import add_chunks_to_vector_store, delete_document_chunks_from_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a PDF file:
    1. Validates it's a PDF.
    2. Uploads the file to S3 (or mock local S3 folder).
    3. Saves metadata to SQLite.
    4. Parses, chunks, embeds, and saves text chunks to FAISS.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    filename = file.filename

    # Check if a document with the same filename already exists.
    # If yes, we overwrite it (clean up old chunks and old storage file first)
    existing_doc = db_models.get_document_by_filename(filename)
    if existing_doc:
        logger.info(f"Document '{filename}' already exists. Overwriting...")
        try:
            # Delete from S3
            storage_service.delete_file(filename)
            # Delete from vector store
            delete_document_chunks_from_vector_store(filename)
            # Delete from DB
            db_models.delete_document(existing_doc["id"])
        except Exception as e:
            logger.warning(f"Error cleaning up old document '{filename}' before overwrite: {e}")

    try:
        # 1. Upload to S3 (or local mock)
        s3_url = storage_service.upload_file(content, filename)

        # 2. Extract text & create chunks
        chunks = process_pdf(content, filename)
        
        # 3. Add chunks to FAISS vector store
        if chunks:
            add_chunks_to_vector_store(chunks)
        else:
            logger.warning(f"No text extracted from '{filename}'. Chunks were not added to vector store.")

        # 4. Save metadata to DB
        doc_id = db_models.add_document(filename, s3_url)
        
        # Get the saved document
        doc_record = db_models.get_document_by_id(doc_id)
        if not doc_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve document metadata after insertion."
            )

        return DocumentResponse(**doc_record)
        
    except Exception as e:
        logger.error(f"Error during file upload process for '{filename}': {e}")
        # Clean up database entry if S3/FAISS upload succeeded but something failed
        try:
            storage_service.delete_file(filename)
            delete_document_chunks_from_vector_store(filename)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while uploading and processing the PDF: {str(e)}"
        )

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """
    Returns a list of all uploaded PDF documents.
    """
    try:
        docs = db_models.get_documents()
        return [DocumentResponse(**doc) for doc in docs]
    except Exception as e:
        logger.error(f"Error fetching documents list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch documents list."
        )

@router.delete("/document/{id}", status_code=status.HTTP_200_OK)
async def delete_document(id: int):
    """
    Deletes a document from SQLite database, S3 storage, and FAISS vector index.
    """
    doc = db_models.get_document_by_id(id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    filename = doc["filename"]
    try:
        # 1. Delete from S3 storage
        storage_service.delete_file(filename)

        # 2. Delete chunks from FAISS vector store
        delete_document_chunks_from_vector_store(filename)

        # 3. Delete from DB
        success = db_models.delete_document(id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document metadata from SQLite."
            )

        return {"detail": f"Document '{filename}' deleted successfully."}
        
    except Exception as e:
        logger.error(f"Error deleting document '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the document: {str(e)}"
        )
