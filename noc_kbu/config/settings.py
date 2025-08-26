"""Configuration settings for NOC KBU."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class IntercomSettings(BaseSettings):
    """Intercom API settings."""
    access_token: str = Field(..., env="INTERCOM_ACCESS_TOKEN")
    base_url: str = Field("https://api.intercom.io", env="INTERCOM_API_BASE_URL")
    
    class Config:
        env_prefix = "INTERCOM_"


class ZendeskSettings(BaseSettings):
    """Zendesk API settings."""
    subdomain: str = Field(..., env="ZENDESK_SUBDOMAIN")
    email: str = Field(..., env="ZENDESK_EMAIL")
    api_token: str = Field(..., env="ZENDESK_API_TOKEN")
    base_url: Optional[str] = Field(None, env="ZENDESK_API_BASE_URL")
    
    @property
    def full_base_url(self) -> str:
        """Get full Zendesk API base URL."""
        if self.base_url:
            return self.base_url
        return f"https://{self.subdomain}.zendesk.com/api/v2"
    
    class Config:
        env_prefix = "ZENDESK_"


class ProcessingSettings(BaseSettings):
    """Content processing settings."""
    batch_size: int = Field(10, env="BATCH_SIZE")
    similarity_threshold: float = Field(0.85, env="SIMILARITY_THRESHOLD")
    quality_threshold: float = Field(0.7, env="QUALITY_SCORE_THRESHOLD")
    max_retries: int = Field(3, env="MAX_RETRIES")
    request_delay: float = Field(1.0, env="REQUEST_DELAY")
    min_content_length: int = Field(50, env="MIN_CONTENT_LENGTH")
    max_content_age_days: int = Field(365, env="MAX_CONTENT_AGE_DAYS")
    
    class Config:
        env_prefix = "PROCESSING_"


class PathSettings(BaseSettings):
    """File path settings."""
    base_dir: Path = Field(Path.cwd(), env="BASE_DIR")
    raw_data_path: Path = Field(Path("data/raw"), env="RAW_DATA_PATH")
    processed_data_path: Path = Field(Path("data/processed"), env="PROCESSED_DATA_PATH")
    approved_data_path: Path = Field(Path("data/approved"), env="APPROVED_DATA_PATH")
    reports_path: Path = Field(Path("reports"), env="REPORTS_PATH")
    
    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        directories = [
            self.raw_data_path,
            self.processed_data_path,
            self.approved_data_path,
            self.reports_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_prefix = "PATH_"


class NOCKBUSettings(BaseSettings):
    """Main NOC KBU configuration."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.intercom = IntercomSettings()
        self.zendesk = ZendeskSettings()
        self.processing = ProcessingSettings()
        self.paths = PathSettings()
        
        # Ensure directories exist
        self.paths.ensure_directories()
    
    # Global settings
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = NOCKBUSettings()


def get_settings() -> NOCKBUSettings:
    """Get global settings instance."""
    return settings


def reload_settings() -> NOCKBUSettings:
    """Reload settings from environment."""
    global settings
    settings = NOCKBUSettings()
    return settings