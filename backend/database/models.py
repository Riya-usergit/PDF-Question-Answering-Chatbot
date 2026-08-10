import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.config.settings import settings

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Establishes a direct connection to the SQLite database file.
    Configures Row factory to allow dictionary-like row querying.
    """
    db_file = settings.db_path
    # Ensure backend directory exists
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row  # Allows fetching columns by name like row['filename']
    return conn

def init_db():
    """
    Creates SQLite database tables if they do not exist yet.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Documents Metadata Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            s3_url TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Chat Log History Table
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
    conn.close()
    logger.info("Database tables initialized successfully.")

# --- Document Helper Functions ---

def add_document(filename: str, s3_url: str) -> int:
    """Inserts a new document record and returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (filename, s3_url, upload_time) VALUES (?, ?, ?)",
        (filename, s3_url, datetime.now().isoformat())
    )
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return doc_id

def get_documents() -> List[Dict[str, Any]]:
    """Fetches all documents ordered by upload time."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, s3_url, upload_time FROM documents ORDER BY upload_time DESC")
    rows = cursor.fetchall()
    # Convert sqlite3.Row items to normal dicts
    docs_list = [dict(row) for row in rows]
    conn.close()
    return docs_list

def get_document_by_id(doc_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves metadata of a document by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, s3_url, upload_time FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_document_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata of a document by its filename."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, s3_url, upload_time FROM documents WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_document(doc_id: int) -> bool:
    """Deletes a document metadata entry by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount > 0

# --- Chat History Helper Functions ---

def add_chat_history(question: str, answer: str, sources: Optional[List[Dict[str, Any]]] = None) -> int:
    """Saves a user query, assistant answer, and sources list to history."""
    sources_str = json.dumps(sources) if sources else "[]"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (question, answer, timestamp, sources) VALUES (?, ?, ?, ?)",
        (question, answer, datetime.now().isoformat(), sources_str)
    )
    conn.commit()
    history_id = cursor.lastrowid
    conn.close()
    return history_id

def get_chat_history() -> List[Dict[str, Any]]:
    """Retrieves all chat records, converting sources JSON back into list format."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer, timestamp, sources FROM chat_history ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    
    history_list = []
    for row in rows:
        item = dict(row)
        # Parse JSON string back to python array
        try:
            item["sources"] = json.loads(item["sources"]) if item["sources"] else []
        except Exception:
            item["sources"] = []
        history_list.append(item)
        
    conn.close()
    return history_list

def clear_chat_history() -> bool:
    """Wipes all rows in chat_history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return True
