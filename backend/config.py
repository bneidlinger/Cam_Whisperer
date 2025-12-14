# backend/config.py
"""
Configuration management for PlatoniCam Backend
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Claude AI Configuration
    anthropic_api_key: str = ""  # Empty string if not set - will trigger warning
    claude_model: str = "claude-sonnet-4-5-20250929"
    claude_max_tokens: int = 4096
    claude_temperature: float = 0.7

    # Database
    database_url: str = "sqlite:///./platonicam.db"

    # File Storage
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    # CORS Settings
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,file://"
    cors_allow_credentials: bool = True

    # Camera Integration
    onvif_timeout_seconds: int = 10
    camera_snapshot_timeout_seconds: int = 15

    # AI Optimization Settings
    ai_optimization_timeout_seconds: int = 30
    fallback_to_heuristic: bool = True
    confidence_threshold: float = 0.6

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security (Future - not used yet)
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Rate Limiting (Future - not used yet)
    max_optimizations_per_hour: Optional[int] = None
    max_cameras_per_site: Optional[int] = None

    # WebRTC Configuration (Phase 3)
    webrtc_enabled: bool = True
    webrtc_signaling_timeout_seconds: int = 30
    webrtc_ice_timeout_seconds: int = 10

    # TURN Server Configuration (for NAT traversal)
    turn_server_url: str = ""  # e.g., "turn:turn.example.com:3478"
    turn_server_urls: str = ""  # Comma-separated list for multiple servers
    turn_username: str = ""
    turn_credential: str = ""
    turn_credential_type: str = "password"  # "password" or "oauth"

    # STUN Server (free, for direct P2P when possible)
    stun_server_urls: str = "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
