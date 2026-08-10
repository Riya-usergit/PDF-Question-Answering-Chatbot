import os
from dotenv import load_dotenv

# Find the project root directory where the '.env' file is located
# File path: project_root/backend/config/settings.py -> project_root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class Settings:
    # 1. Google Gemini API Credentials
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # 2. Supabase Storage Credentials
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "pdf-bot-bucket")

    # 3. Toggle to run offline using a local storage folder instead of Supabase
    # Standardizes the string from environment to a Python boolean
    _mock_env = os.getenv("LOCAL_MOCK_STORAGE", "True")
    LOCAL_MOCK_STORAGE = _mock_env.lower() in ("true", "1", "yes")

    # 4. Folder paths inside the backend directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # project_root/backend
    DATABASE_NAME = "database.db"

    @property
    def db_path(self) -> str:
        # Path to the SQLite database file: backend/database.db
        return os.path.join(self.BASE_DIR, self.DATABASE_NAME)

    @property
    def local_storage_dir(self) -> str:
        # Path to local storage folder for PDF uploads: backend/local_storage
        return os.path.join(self.BASE_DIR, "local_storage")

    @property
    def faiss_index_dir(self) -> str:
        # Path to the directory where FAISS indexes will be saved: backend/faiss_index
        return os.path.join(self.BASE_DIR, "faiss_index")

# Instantiate a single config settings object to import elsewhere
settings = Settings()
