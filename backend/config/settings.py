import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    # Gemini API Credentials
    GEMINI_API_KEY: str

    # Supabase Storage Settings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_BUCKET_NAME: str = "pdf-bot-bucket"

    # Mock settings
    LOCAL_MOCK_STORAGE: bool = True

    # Database file name
    DATABASE_NAME: str = "database.db"

    # Base Directory paths
    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @property
    def db_path(self) -> str:
        return os.path.join(self.base_dir, self.DATABASE_NAME)

    @property
    def local_storage_dir(self) -> str:
        return os.path.join(self.base_dir, "local_storage")

    @property
    def faiss_index_dir(self) -> str:
        return os.path.join(self.base_dir, "faiss_index")

    # Load from .env file at the project root level
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v or v == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY must be configured with a valid Google Gemini API key.")
        return v

# Instantiate settings
try:
    settings = Settings()
except Exception as e:
    print(f"[Configuration Error] Failed to load configuration: {e}")
    raise e
