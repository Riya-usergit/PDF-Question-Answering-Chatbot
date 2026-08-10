import os
import logging
from backend.config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    """
    Handles PDF file storage. Supports saving files:
    - Locally in a folder (for easy beginner testing).
    - In Supabase Storage (for cloud production).
    """
    def __init__(self):
        self.local_mock = settings.LOCAL_MOCK_STORAGE
        self.bucket_name = settings.SUPABASE_BUCKET_NAME
        self.supabase_url = settings.SUPABASE_URL.rstrip('/')
        
        # Check if Supabase keys exist. If keys are missing, force local folder mode.
        has_creds = bool(settings.SUPABASE_URL and settings.SUPABASE_KEY and self.bucket_name)
        
        if not has_creds or self.local_mock:
            self.local_mock = True
            # Create local folder for files: backend/local_storage
            os.makedirs(settings.local_storage_dir, exist_ok=True)
            logger.info(f"Local Storage Active. Files are saved in: {settings.local_storage_dir}")
            self.client = None
        else:
            try:
                # Load client dynamically so we don't crash if SDK is not installed yet
                from supabase import create_client
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("Connected to Supabase Storage client.")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}. Falling back to local storage.")
                self.local_mock = True
                os.makedirs(settings.local_storage_dir, exist_ok=True)
                self.client = None

    def upload_file(self, file_content: bytes, filename: str) -> str:
        """
        Saves file bytes to storage.
        Returns the path URL to access it.
        """
        if self.local_mock:
            # 1. Local Fallback Mode: Save directly to a local folder
            filepath = os.path.join(settings.local_storage_dir, filename)
            with open(filepath, "wb") as f:
                f.write(file_content)
            logger.info(f"Mock Upload: Saved file '{filename}' locally.")
            return f"local://{filename}"
        else:
            try:
                # 2. Cloud Mode: Upload to Supabase Storage
                # upsert=true enables overwriting a file if it already exists
                self.client.storage.from_(self.bucket_name).upload(
                    path=filename,
                    file=file_content,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
                logger.info(f"Supabase Upload: Saved '{filename}' in cloud. URL: {public_url}")
                return public_url
            except Exception as e:
                logger.error(f"Supabase Upload failed for '{filename}': {e}")
                raise RuntimeError(f"Storage Upload Failed: {e}")

    def download_file(self, filename: str) -> bytes:
        """
        Downloads and returns the file as raw bytes.
        """
        if self.local_mock:
            # 1. Local Fallback Mode: Read bytes from disk
            filepath = os.path.join(settings.local_storage_dir, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File '{filename}' does not exist on disk.")
            with open(filepath, "rb") as f:
                return f.read()
        else:
            try:
                # 2. Cloud Mode: Download from Supabase Bucket
                file_bytes = self.client.storage.from_(self.bucket_name).download(filename)
                return file_bytes
            except Exception as e:
                logger.error(f"Supabase Download failed for '{filename}': {e}")
                raise RuntimeError(f"Storage Download Failed: {e}")

    def delete_file(self, filename: str) -> bool:
        """
        Deletes the file from storage.
        """
        if self.local_mock:
            # 1. Local Fallback Mode: Remove file from folder
            filepath = os.path.join(settings.local_storage_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Mock Delete: Removed file '{filename}' from local disk.")
                return True
            return False
        else:
            try:
                # 2. Cloud Mode: Remove from Supabase Bucket
                # remove() accepts a list of file paths
                self.client.storage.from_(self.bucket_name).remove([filename])
                logger.info(f"Supabase Delete: Removed '{filename}' from cloud.")
                return True
            except Exception as e:
                logger.error(f"Supabase Delete failed for '{filename}': {e}")
                raise RuntimeError(f"Storage Delete Failed: {e}")

# Single global instance of the storage service
storage_service = StorageService()
