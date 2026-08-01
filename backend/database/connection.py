import sqlite3
import os
from contextlib import contextmanager
from backend.config.settings import settings

@contextmanager
def get_db_connection():
    db_file = settings.db_path
    
    # Ensure backend directory exists (where db is saved)
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects
    try:
        yield conn
    finally:
        conn.close()
