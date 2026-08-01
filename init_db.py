import logging
from backend.database.models import init_db

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Initializing SQLite database tables...")
    init_db()
    print("Database tables initialized successfully!")
