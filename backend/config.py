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

    # TLS/SSL Configuration (Phase 5 Security)
    tls_verify_certificates: bool = False  # Set True for production with proper certs
    tls_allow_self_signed: bool = True  # Allow self-signed certs (common in cameras)
    tls_ca_bundle_path: str = ""  # Path to custom CA bundle (optional)
    tls_client_cert_path: str = ""  # Path to client certificate (optional)
    tls_client_key_path: str = ""  # Path to client private key (optional)

    # MQTT Configuration (Phase 4 - Profile M Events)
    mqtt_enabled: bool = False  # Enable MQTT event bridge
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_use_tls: bool = False
    mqtt_ca_cert_path: str = ""
    mqtt_client_id: str = ""  # Auto-generated if empty
    mqtt_topic_prefix: str = "platonicam"

    # Emergency Recording Configuration
    emergency_record_enabled: bool = True
    emergency_record_storage_path: str = "./emergency_snapshots"
    emergency_record_max_storage_gb: float = 10.0
    emergency_record_cleanup_interval_minutes: int = 60
    emergency_record_default_retention_hours: int = 24
    emergency_record_max_concurrent_captures: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
