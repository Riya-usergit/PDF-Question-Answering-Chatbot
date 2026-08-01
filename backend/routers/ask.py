import logging
from fastapi import APIRouter, HTTPException, status
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.config.settings import settings
from backend.models.schemas import AskRequest, AskResponse, SourceCitation
from backend.rag.vector_store import search_similarity
from backend.database import models as db_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["query"])

# Initialize Gemini Chat Model using LangChain
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.0  # High precision, low creativity for QA accuracy
    )
    logger.info("LangChain Gemini 3.5 Flash client initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing LangChain Gemini LLM client: {e}")
    llm = None

@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Asks a question about the uploaded PDFs:
    1. Converts question into embedding & retrieves top-k chunks from FAISS.
    2. Builds a context-aware system prompt.
    3. Calls Gemini LLM with strict constraints (no hallucination).
    4. Saves the interaction (question, answer, citations) to SQLite chat history.
    """
    if not llm:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini LLM model service is not available. Please verify your GEMINI_API_KEY configuration."
        )

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question text cannot be empty."
        )

    # Check if we have documents uploaded first
    existing_docs = db_models.get_documents()
    if not existing_docs:
        # Return a friendly guide message rather than error, so the user knows they need to upload PDFs first
        return AskResponse(
            answer="Please upload one or more PDF files in the sidebar before asking questions.",
            sources=[]
        )

    try:
        # 1. Similarity Search (retrieving top 5 chunks)
        # Using k=5 provides balanced context coverage while keeping token counts inside Gemini's prompt limit
        retrieved_docs = search_similarity(question, k=5)

        if not retrieved_docs:
            return AskResponse(
                answer="No relevant text could be found in the uploaded documents. Please try a different query.",
                sources=[]
            )

        # 2. Extract citations and compile context string
        context_parts = []
        sources_list = []
        
        for doc in retrieved_docs:
            src_filename = doc.metadata.get("source", "Unknown PDF")
            src_page = doc.metadata.get("page", 0)
            
            context_parts.append(
                f"Source Document: {src_filename} | Page: {src_page}\n"
                f"Content Snippet: {doc.page_content.strip()}"
            )
            
            # Store citation dictionary if it doesn't already exist in the list
            citation = SourceCitation(filename=src_filename, page=src_page)
            if citation not in sources_list:
                sources_list.append(citation)

        context_string = "\n\n---\n\n".join(context_parts)

        # 3. Create instruction-tuned System Prompt
        system_instruction = (
            "You are a helpful and precise assistant. Your goal is to answer the user's question using ONLY the provided context blocks below.\n"
            "Each context block is prefixed with 'Source Document: <filename> | Page: <number>' followed by the text contents.\n\n"
            "Strict constraints:\n"
            "1. Answer the question using ONLY the provided context. Do NOT use any pre-existing knowledge or make assumptions.\n"
            "2. If the context does not contain the answer, say exactly: "
            "'I cannot find the answer in the uploaded documents.'\n"
            "3. Do not speculative, extrapolate, or hallucinate.\n"
            "4. Be concise and write a clear, factual answer.\n\n"
            f"CONTEXT BLOCKS:\n{context_string}"
        )

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=question)
        ]

        # 4. Generate answer from Gemini LLM
        response = llm.invoke(messages)
        
        # Safely extract text content (supports string, list of blocks, or dicts)
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

        # 5. Clean up output (in case LLM starts adding headers/extra text)
        if not answer:
            answer = "I cannot find the answer in the uploaded documents."

        # If LLM indicates lack of answer, we omit citations
        if "cannot find the answer" in answer.lower():
            sources_list = []

        # 6. Save chat history to DB (sources stored as JSON internally)
        sources_dict_list = [{"filename": s.filename, "page": s.page} for s in sources_list]
        db_models.add_chat_history(question, answer, sources_dict_list)

        return AskResponse(answer=answer, sources=sources_list)

    except Exception as e:
        logger.error(f"Error answering question '{question}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the answer: {str(e)}"
        )
