import logging
from fastapi import APIRouter, HTTPException, status
from typing import List
from backend.models.schemas import ChatHistoryItem
from backend.database import models as db_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["history"])

@router.get("/history", response_model=List[ChatHistoryItem])
async def get_history():
    """
    Retrieves the complete chat history list (ordered chronologically).
    """
    try:
        history = db_models.get_chat_history()
        return [ChatHistoryItem(**item) for item in history]
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history."
        )

@router.delete("/history", status_code=status.HTTP_200_OK)
async def clear_history():
    """
    Clears all conversations from the database.
    """
    try:
        db_models.clear_chat_history()
        return {"detail": "Chat history cleared successfully."}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history."
        )
