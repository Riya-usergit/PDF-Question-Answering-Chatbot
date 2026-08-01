import os
import sys
import logging

# Append workspace path to system path for running as script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.config.settings import settings
from backend.database.models import init_db, get_documents
from backend.rag.embeddings import embeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerificationAgent")

def verify_system():
    logger.info("==== STARTING RAG SYSTEM VERIFICATION ====")
    
    # 1. Load settings and verify API keys
    logger.info("1. Verifying Settings...")
    logger.info(f"   Database Path: {settings.db_path}")
    logger.info(f"   Local Storage Mock Mode: {settings.LOCAL_MOCK_STORAGE}")
    logger.info(f"   Local Storage Directory: {settings.local_storage_dir}")
    logger.info(f"   FAISS Directory: {settings.faiss_index_dir}")
    
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
         logger.error("   ❌ GEMINI_API_KEY is not configured correctly.")
         sys.exit(1)
    logger.info("   ✅ Gemini API key configured.")

    # 2. Database connection & initialization
    logger.info("2. Initializing SQLite Database...")
    try:
        init_db()
        docs = get_documents()
        logger.info(f"   ✅ Database connected successfully. Found {len(docs)} documents.")
    except Exception as e:
        logger.error(f"   ❌ Database check failed: {e}")
        sys.exit(1)

    # 3. Load HuggingFace embeddings model
    logger.info("3. Initializing HuggingFace Embeddings Model (all-MiniLM-L6-v2)...")
    try:
        test_text = "This is a simple embedding test query."
        embedded_vec = embeddings.embed_query(test_text)
        logger.info(f"   ✅ Embeddings model loaded successfully. Output vector dimensions: {len(embedded_vec)}")
    except Exception as e:
        logger.error(f"   ❌ HuggingFace Embeddings initialization failed: {e}")
        sys.exit(1)

    logger.info("==== VERIFICATION SUCCESSFUL: SYSTEM READY ====")

if __name__ == "__main__":
    verify_system()
