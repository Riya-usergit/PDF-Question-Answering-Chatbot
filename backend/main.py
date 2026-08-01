import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.models import init_db
from backend.routers import upload, ask, history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup database initialization and lifecycle events.
    """
    logger.info("Starting up FastAPI application...")
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Failed to initialize SQLite database during startup: {e}")
        raise e
    yield
    logger.info("Shutting down FastAPI application...")

# Initialize FastAPI App
app = FastAPI(
    title="AI PDF Question Answering Chatbot API",
    description="A production-ready FastAPI backend for retrieving and answering queries about PDF files using LangChain, FAISS, and Gemini.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
# Essential since the Streamlit frontend and FastAPI backend run on different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to specific origins (e.g. ['http://localhost:8501'])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload.router)
app.include_router(ask.router)
app.include_router(history.router)

@app.get("/", tags=["health"])
async def health_check():
    """
    Simple API health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "AI PDF QA Chatbot Backend",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
