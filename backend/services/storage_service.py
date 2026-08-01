import os
import logging
from backend.config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.local_mock = settings.LOCAL_MOCK_STORAGE
        self.bucket_name = settings.SUPABASE_BUCKET_NAME
        self.supabase_url = settings.SUPABASE_URL.rstrip('/')
        
        # Verify if Supabase environment keys are set
        has_supabase_creds = bool(settings.SUPABASE_URL and settings.SUPABASE_KEY and self.bucket_name)
        
        if not has_supabase_creds or self.local_mock:
            if not has_supabase_creds and not self.local_mock:
                logger.warning("Supabase credentials not configured in .env. Falling back to local storage.")
            self.local_mock = True
            os.makedirs(settings.local_storage_dir, exist_ok=True)
            logger.info(f"Local storage mock enabled. Directory: {settings.local_storage_dir}")
            self.client = None
        else:
            try:
                # Lazy import to prevent app from crashing immediately if library isn't installed yet
                from supabase import create_client
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}. Falling back to local storage mock.")
                self.local_mock = True
                os.makedirs(settings.local_storage_dir, exist_ok=True)
                self.client = None

    def upload_file(self, file_content: bytes, filename: str) -> str:
        """
        Uploads a file to Supabase Storage or local storage.
        Returns the access URL string.
        """
        if self.local_mock:
            dest_path = os.path.join(settings.local_storage_dir, filename)
            with open(dest_path, "wb") as f:
                f.write(file_content)
            mock_url = f"local://{filename}"
            logger.info(f"Mock Storage Upload: Saved file '{filename}' locally at {dest_path}")
            return mock_url
        else:
            try:
                # Upload to Supabase Storage
                # We use the upsert=true option in file_options to overwrite existing files cleanly
                self.client.storage.from_(self.bucket_name).upload(
                    path=filename,
                    file=file_content,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                # Retrieve public URL for access
                # Can also build it deterministically to avoid extra network lookups:
                public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
                logger.info(f"Supabase Storage Upload: '{filename}' uploaded successfully. URL: {public_url}")
                return public_url
            except Exception as e:
                logger.error(f"Supabase Storage Upload Failed for '{filename}': {e}")
                # Raise to be handled gracefully by callers (routers)
                raise RuntimeError(f"Supabase Upload Failed: {e}")

    def download_file(self, filename: str) -> bytes:
        """
        Downloads the file's binary contents.
        """
        if self.local_mock:
            filepath = os.path.join(settings.local_storage_dir, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Local mock file '{filename}' does not exist at {filepath}")
            with open(filepath, "rb") as f:
                return f.read()
        else:
            try:
                response_bytes = self.client.storage.from_(self.bucket_name).download(filename)
                return response_bytes
            except Exception as e:
                logger.error(f"Supabase Storage Download Failed for '{filename}': {e}")
                raise RuntimeError(f"Supabase Download Failed: {e}")

    def delete_file(self, filename: str) -> bool:
        """
        Deletes the file from storage.
        """
        if self.local_mock:
            filepath = os.path.join(settings.local_storage_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Mock Storage Delete: Deleted '{filename}' from {filepath}")
                return True
            return False
        else:
            try:
                # Supabase delete takes a list of paths
                self.client.storage.from_(self.bucket_name).remove([filename])
                logger.info(f"Supabase Storage Delete: Deleted file '{filename}' from bucket '{self.bucket_name}'")
                return True
            except Exception as e:
                logger.error(f"Supabase Storage Delete Failed for '{filename}': {e}")
                raise RuntimeError(f"Supabase Delete Failed: {e}")

# Instantiate storage service
storage_service = StorageService()
