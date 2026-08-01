import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

def process_pdf(pdf_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parses PDF bytes, extracts text page-by-page, and splits text into chunks.
    Maintains a 1-based page index for citations.
    
    Returns:
        List[Dict[str, Any]]: List of dicts, each with 'text' and 'metadata' (source and page).
    """
    try:
        # Open PDF from memory bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF file {filename}: {e}")
        raise ValueError(f"Invalid PDF file: {e}")

    # Set up splitter
    # 1000 characters chunk size with 200 characters overlap represents a standard, robust setting for RAG
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunks_with_metadata = []
    total_pages = len(doc)
    logger.info(f"Processing PDF '{filename}' with {total_pages} pages...")

    for page_idx in range(total_pages):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        
        # Skip empty pages
        if not text:
            continue

        # Split page text into chunks
        page_chunks = text_splitter.split_text(text)
        
        for chunk in page_chunks:
            # We filter out very short, non-informative chunks (e.g. page headers/footers containing just numbers)
            if len(chunk.strip()) < 10:
                continue
            chunks_with_metadata.append({
                "text": chunk,
                "metadata": {
                    "source": filename,
                    "page": page_idx + 1  # 1-indexed page
                }
            })

    doc.close()
    logger.info(f"Finished processing '{filename}'. Generated {len(chunks_with_metadata)} chunks.")
    return chunks_with_metadata
