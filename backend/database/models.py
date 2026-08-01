import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database.connection import get_db_connection

logger = logging.getLogger(__name__)

def init_db():
    """Initializes the database schema if tables do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                s3_url TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create chat_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sources TEXT
            )
        """)
        
        conn.commit()
    logger.info("SQLite database tables initialized successfully.")

# Document operations
def add_document(filename: str, s3_url: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, s3_url, upload_time) VALUES (?, ?, ?)",
            (filename, s3_url, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid

def get_documents() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, s3_url, upload_time FROM documents ORDER BY upload_time DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_document_by_id(doc_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, s3_url, upload_time FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_document_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, s3_url, upload_time FROM documents WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_document(doc_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0

# Chat history operations
def add_chat_history(question: str, answer: str, sources: Optional[List[Dict[str, Any]]] = None) -> int:
    sources_str = json.dumps(sources) if sources else "[]"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (question, answer, timestamp, sources) VALUES (?, ?, ?, ?)",
            (question, answer, datetime.now().isoformat(), sources_str)
        )
        conn.commit()
        return cursor.lastrowid

def get_chat_history() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, answer, timestamp, sources FROM chat_history ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            item = dict(row)
            try:
                item["sources"] = json.loads(item["sources"]) if item["sources"] else []
            except Exception:
                item["sources"] = []
            history.append(item)
        return history

def clear_chat_history() -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history")
        conn.commit()
        return True
