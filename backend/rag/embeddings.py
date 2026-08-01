import logging
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

logger.info("Initializing HuggingFace Embeddings model (all-MiniLM-L6-v2)...")

try:
    # Set up LangChain HF embeddings model wrapper
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},  # Default to CPU for portability
        encode_kwargs={'normalize_embeddings': True}
    )
    logger.info("HuggingFace Embeddings model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading HuggingFace Embeddings model: {e}")
    raise e
