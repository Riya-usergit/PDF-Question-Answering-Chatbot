import os
import logging
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from backend.config.settings import settings
from backend.rag.embeddings import embeddings

logger = logging.getLogger(__name__)

INDEX_NAME = "pdf_rag_index"

def get_vector_store() -> FAISS:
    """
    Loads the FAISS index from local disk.
    Returns None if the index files do not exist.
    """
    index_path = settings.faiss_index_dir
    faiss_file = os.path.join(index_path, f"{INDEX_NAME}.faiss")
    pkl_file = os.path.join(index_path, f"{INDEX_NAME}.pkl")
    
    if not os.path.exists(faiss_file) or not os.path.exists(pkl_file):
        logger.info("No existing FAISS index files found on disk.")
        return None
        
    try:
        # Load local FAISS index with allow_dangerous_deserialization=True 
        # (safe since we only load index files created by this application locally)
        db = FAISS.load_local(
            index_path, 
            embeddings, 
            index_name=INDEX_NAME, 
            allow_dangerous_deserialization=True
        )
        logger.info("FAISS index loaded successfully from disk.")
        return db
    except Exception as e:
        logger.error(f"Error loading FAISS index: {e}")
        return None

def save_vector_store(db: FAISS):
    """
    Saves the FAISS index to local disk.
    """
    index_path = settings.faiss_index_dir
    os.makedirs(index_path, exist_ok=True)
    try:
        db.save_local(index_path, index_name=INDEX_NAME)
        logger.info(f"FAISS index saved successfully at: {index_path}")
    except Exception as e:
        logger.error(f"Error saving FAISS index: {e}")
        raise e

def add_chunks_to_vector_store(chunks: List[Dict[str, Any]]):
    """
    Converts chunk dictionaries to LangChain Documents, adds them to
    the FAISS index, and persists the index.
    """
    if not chunks:
        logger.info("No chunks to add to the vector store.")
        return
        
    documents = [
        Document(page_content=chunk["text"], metadata=chunk["metadata"])
        for chunk in chunks
    ]
    
    db = get_vector_store()
    if db is None:
        logger.info("Creating a new FAISS vector store...")
        db = FAISS.from_documents(documents, embeddings)
    else:
        logger.info(f"Adding {len(documents)} documents to the existing FAISS index...")
        db.add_documents(documents)
        
    save_vector_store(db)

def delete_document_chunks_from_vector_store(filename: str) -> bool:
    """
    Finds and deletes all FAISS index entries associated with the specified filename.
    If the index becomes completely empty, deletes the index files from disk.
    """
    db = get_vector_store()
    if db is None:
        logger.warning(f"Attempted to delete chunks for '{filename}', but FAISS store is empty.")
        return False
        
    # Search docstore keys for matches
    ids_to_delete = []
    # LangChain FAISS uses a dict mapping doc_id string to Document
    for doc_id, doc in db.docstore._dict.items():
        if doc.metadata.get("source") == filename:
            ids_to_delete.append(doc_id)
            
    if not ids_to_delete:
        logger.info(f"No chunks found in FAISS for filename '{filename}'.")
        return False
        
    total_docs_before = len(db.docstore._dict)
    logger.info(f"Found {len(ids_to_delete)} chunks matching '{filename}' to delete.")
    
    # If we are deleting everything, wipe the files
    if len(ids_to_delete) >= total_docs_before:
        logger.info("Deleting entire index because all documents were removed.")
        index_path = settings.faiss_index_dir
        for file_ext in [".faiss", ".pkl"]:
            file_path = os.path.join(index_path, f"{INDEX_NAME}{file_ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        db.delete(ids_to_delete)
        save_vector_store(db)
        
    return True

def search_similarity(query: str, k: int = 5) -> List[Document]:
    """
    Searches the FAISS vector store for top-k similar chunks to the query.
    """
    db = get_vector_store()
    if db is None:
        logger.warning("Similarity search called but vector store is empty.")
        return []
    
    # Return matches
    return db.similarity_search(query, k=k)
