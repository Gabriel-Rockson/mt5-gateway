import logging
import os


class Config:
    MT5_API_PORT = int(os.getenv('MT5_API_PORT', '5001'))

    MT5_RECONNECT_ATTEMPTS = int(os.getenv('MT5_RECONNECT_ATTEMPTS', '3'))

    MT5_RECONNECT_BASE_DELAY = float(os.getenv('MT5_RECONNECT_BASE_DELAY', '1.0'))

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    @classmethod
    def validate(cls):
        logger = logging.getLogger(__name__)

        if cls.MT5_RECONNECT_ATTEMPTS < 1:
            raise ValueError("MT5_RECONNECT_ATTEMPTS must be at least 1")

        if cls.MT5_RECONNECT_BASE_DELAY <= 0:
            raise ValueError("MT5_RECONNECT_BASE_DELAY must be positive")

        if cls.LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"Invalid LOG_LEVEL: {cls.LOG_LEVEL}")

        logger.info("Configuration validated successfully")
