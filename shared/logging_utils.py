"""
Structured Logging Utility for Agent Skill Marketplace.
"""

import sys
import logging
from typing import Optional

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Returns a configured logger writing to stderr so stdout remains clean for JSON output.
    """
    logger = logging.getLogger(f"agent_marketplace.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger
