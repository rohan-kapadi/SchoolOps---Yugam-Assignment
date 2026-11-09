"""Configuration settings for SchoolOps AI agent services."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Service URLs and Database
SCHOOL_API_URL: str = os.getenv("SCHOOL_API_URL", "http://127.0.0.1:8001").rstrip("/")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
DB_PATH: str = os.getenv("DB_PATH", "schoolops.db")
SENDER_FAIL_RATE: float = float(os.getenv("SENDER_FAIL_RATE", "0.2"))

# HTTP Client Configuration
DEFAULT_HTTP_TIMEOUT: float = float(os.getenv("DEFAULT_HTTP_TIMEOUT", "10.0"))

# External API URLs
OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
INDIA_POST_PIN_URL: str = "https://api.postalpincode.in/pincode"

# Cache TTLs (in seconds)
CACHE_TTL_FORECAST: int = 15 * 60       # 15 minutes
CACHE_TTL_AIR_QUALITY: int = 30 * 60    # 30 minutes
CACHE_TTL_LOCATION: int = 24 * 60 * 60  # 24 hours

# Forecast Constraints
AQI_MAX_FORECAST_DAYS: int = 7

# Default School Coordinates (Jaipur, Rajasthan)
DEFAULT_SCHOOL_LAT: float = 26.9124
DEFAULT_SCHOOL_LON: float = 75.7873
