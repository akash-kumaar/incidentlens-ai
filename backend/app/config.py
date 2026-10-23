import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "IncidentLens AI"
    version: str = "1.0.0"
    debug: bool = False

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # AWS / Bedrock
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    ai_provider: str = "local"  # "local" | "bedrock"

    # S3
    s3_bucket: Optional[str] = None
    s3_reports_prefix: str = "incidentlens/reports/"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
