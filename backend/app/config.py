from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    hy3_api_key: str
    hy3_base_url: str = "https://tokenhub.tencentmaas.com/v1"
    hy3_model: str = "hy3"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    upload_dir: Path = Path("uploads")
    max_upload_size_mb: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
