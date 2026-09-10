"""
Security and Production Hardening Utilities for Agent Skill Marketplace.
Provides:
  1. SSRF and private-network target URL validation
  2. Path traversal and sensitive system directory write protection
  3. Secret and credential masking in logs and terminal output
  4. Strict CLI input boundary and argument sanitization
"""

import os
import re
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, List, Optional


def is_safe_url(url: str, allow_private: bool = False) -> Tuple[bool, str]:
    """
    Validates URL safety against SSRF (Server-Side Request Forgery) attacks.
    Blocks:
      - Non-HTTP/HTTPS schemes (file://, gopher://, ftp://, etc.)
      - Localhost and loopback addresses (127.0.0.0/8, ::1)
      - Link-local and cloud instance metadata services (169.254.169.254, metadata.google.internal)
      - Private RFC-1918 subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) unless allow_private=True
    """
    if not url or not isinstance(url, str):
        return False, "Target URL must be a non-empty string"

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Malformed URL format"

    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in target URL"

    hostname_lower = hostname.lower()

    # Cloud metadata endpoints
    BLOCKED_HOSTNAMES = {
        "metadata.google.internal",
        "metadata",
        "instance-data",
        "169.254.169.254",
    }
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Access to cloud instance metadata service '{hostname}' is prohibited (SSRF prevention)"

    if not allow_private:
        if hostname_lower in ("localhost", "127.0.0.1", "::1") or hostname_lower.endswith(".localhost") or hostname_lower.endswith(".local"):
            return False, "Access to localhost or local network services is prohibited (SSRF prevention)"

        try:
            ip = ipaddress.ip_address(hostname_lower)
            if ip.is_loopback:
                return False, f"Loopback address '{hostname}' is blocked (SSRF prevention)"
            if ip.is_link_local:
                return False, f"Link-local address '{hostname}' is blocked (SSRF prevention)"
            if ip.is_private:
                return False, f"Private network address '{hostname}' is blocked (SSRF prevention)"
            if ip.is_reserved or ip.is_multicast:
                return False, f"Reserved / multicast address '{hostname}' is blocked"
        except ValueError:
            # Hostname is a domain name, not an IP literal
            pass

    return True, ""


def is_safe_output_path(filepath: str) -> Tuple[bool, str]:
    """
    Validates output file paths to prevent directory traversal and overwriting sensitive files.
    Returns (is_safe: bool, canonical_path_or_error: str).
    """
    if not filepath or not isinstance(filepath, str):
        return False, "Output path cannot be empty"

    if "\x00" in filepath:
        return False, "Null bytes are prohibited in file paths"

    resolved = os.path.abspath(filepath)
    resolved_lower = resolved.lower()

    # Block writing to sensitive system directories
    DANGEROUS_SYSTEM_ROOTS = [
        "c:\\windows",
        "c:\\program files",
        "/etc",
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/var/run",
        "/boot",
        "/sys",
        "/proc",
    ]
    for sys_root in DANGEROUS_SYSTEM_ROOTS:
        if resolved_lower.startswith(sys_root):
            return False, f"Writing to sensitive system directory '{sys_root}' is prohibited"

    return True, resolved


def mask_secrets(text: str, extra_secrets: Optional[List[str]] = None) -> str:
    """
    Redacts known API key patterns and explicit secret strings from logs and output.
    """
    if not text:
        return text

    sanitized = text

    # Redact explicit strings passed
    if extra_secrets:
        for sec in extra_secrets:
            if sec and len(sec) > 5 and sec in sanitized:
                sanitized = sanitized.replace(sec, "***REDACTED***")

    # Common API key patterns
    sanitized = re.sub(r"AIzaSy[A-Za-z0-9_-]{33}", "AIzaSy***REDACTED***", sanitized)
    sanitized = re.sub(r"sk-[A-Za-z0-9]{20,}", "sk-***REDACTED***", sanitized)
    sanitized = re.sub(r"bearer\s+[A-Za-z0-9._-]{20,}", "Bearer ***REDACTED***", sanitized, flags=re.IGNORECASE)

    return sanitized


def validate_runtime_bounds(
    max_pages: int,
    max_depth: int,
    timeout_seconds: float
) -> Tuple[bool, str]:
    """
    Enforces safe bounds on crawler runtime parameters to prevent resource exhaustion / DoS.
    """
    if not (1 <= max_pages <= 200):
        return False, f"Invalid max_pages ({max_pages}). Must be between 1 and 200."

    if not (1 <= max_depth <= 10):
        return False, f"Invalid max_depth ({max_depth}). Must be between 1 and 10."

    if not (1.0 <= timeout_seconds <= 60.0):
        return False, f"Invalid timeout ({timeout_seconds}). Must be between 1.0 and 60.0 seconds."

    return True, ""
