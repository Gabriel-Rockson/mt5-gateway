import logging
import os


class Config:
    MT5_API_PORT = int(os.getenv('MT5_API_PORT', '5001'))

    MT5_RECONNECT_ATTEMPTS = int(os.getenv('MT5_RECONNECT_ATTEMPTS', '3'))

    MT5_RECONNECT_BASE_DELAY = float(os.getenv('MT5_RECONNECT_BASE_DELAY', '1.0'))

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Shared secret required on the X-API-Key header for every request except
    # /health/* probes. Required — startup fails loudly if not set. Generate
    # with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    MT5_API_KEY = os.getenv('MT5_API_KEY', '')

    @classmethod
    def validate(cls):
        logger = logging.getLogger(__name__)

        if cls.MT5_RECONNECT_ATTEMPTS < 1:
            raise ValueError("MT5_RECONNECT_ATTEMPTS must be at least 1")

        if cls.MT5_RECONNECT_BASE_DELAY <= 0:
            raise ValueError("MT5_RECONNECT_BASE_DELAY must be positive")

        if cls.LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"Invalid LOG_LEVEL: {cls.LOG_LEVEL}")

        if not cls.MT5_API_KEY:
            raise ValueError(
                "MT5_API_KEY env var is required — gateway exposes order placement and "
                "account state; without it the API would be open to anyone who can reach "
                "the port. Generate: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(cls.MT5_API_KEY) < 32:
            raise ValueError(
                f"MT5_API_KEY is too short ({len(cls.MT5_API_KEY)} chars) — minimum 32"
            )

        logger.info("Configuration validated successfully")
