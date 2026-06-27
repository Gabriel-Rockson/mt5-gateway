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

    # Optional HTTP Basic credentials for the API docs (/apidocs). The docs are
    # exempt from the X-API-Key check; set both to put a browser login in front
    # of them. Leave both unset to keep the docs public. Setting only one is a
    # misconfiguration and fails validation.
    MT5_DOCS_USER = os.getenv('MT5_DOCS_USER', '')
    MT5_DOCS_PASSWORD = os.getenv('MT5_DOCS_PASSWORD', '')

    @classmethod
    def docs_auth_enabled(cls) -> bool:
        return bool(cls.MT5_DOCS_USER and cls.MT5_DOCS_PASSWORD)

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

        if bool(cls.MT5_DOCS_USER) != bool(cls.MT5_DOCS_PASSWORD):
            raise ValueError(
                "MT5_DOCS_USER and MT5_DOCS_PASSWORD must be set together — set both "
                "to password-protect /apidocs, or neither to leave the docs public"
            )

        if not cls.docs_auth_enabled():
            logger.warning(
                "API docs (/apidocs) are public — set MT5_DOCS_USER and "
                "MT5_DOCS_PASSWORD to require a login"
            )

        logger.info("Configuration validated successfully")
