"""
Structured Logging Utility for Agent Skill Marketplace.
"""

import sys
import logging
from typing import Optional
from shared.security import mask_secrets

class SecretRedactionFilter(logging.Filter):
    """Prevents accidental leakage of tokens, API keys, or secrets in logs."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_secrets(record.msg)
        return True

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Returns a configured logger writing to stderr so stdout remains clean for JSON output.
    Applies secret redaction filter automatically.
    """
    logger = logging.getLogger(f"agent_marketplace.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactionFilter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger
