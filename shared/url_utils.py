"""
URL Parsing, Validation, and Normalization Utilities.
"""

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, urljoin
import re
from typing import Optional, Set

def is_valid_url(url: str) -> bool:
    """Checks if a string is a valid HTTP/HTTPS URL with a netloc."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    Normalizes a URL for deduplication and crawling:
    - Lowercases scheme and host
    - Strips fragment (#)
    - Strips standard default ports (80 for http, 443 for https)
    - Sorts query parameters
    - Normalizes empty paths to '/'
    """
    if not is_valid_url(url):
        raise ValueError(f"Invalid URL provided for normalization: {url}")

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove default port numbers if present
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize path
    path = parsed.path
    if not path:
        path = "/"

    # Sort query parameters deterministically
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    sorted_query = urlencode(sorted(query_params))

    # Strip fragment completely
    fragment = ""

    return urlunparse((scheme, netloc, path, parsed.params, sorted_query, fragment))

def get_domain(url: str) -> str:
    """Extracts the registered domain / hostname from a URL."""
    if not is_valid_url(url):
        return ""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    # Strip port if present
    if ":" in netloc:
        netloc = netloc.split(":")[0]
    return netloc

def is_same_domain(url1: str, url2: str) -> bool:
    """Checks whether two URLs share the exact same domain / host."""
    d1 = get_domain(url1)
    d2 = get_domain(url2)
    return bool(d1 and d2 and d1 == d2)

def resolve_relative_url(base_url: str, relative_url: str) -> Optional[str]:
    """Resolves a relative URL string against a base URL."""
    if not relative_url or not isinstance(relative_url, str):
        return None
    relative_url = relative_url.strip()
    if relative_url.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    try:
        joined = urljoin(base_url, relative_url)
        if is_valid_url(joined):
            return normalize_url(joined)
        return None
    except Exception:
        return None

class URLDeduplicator:
    """Thread-safe / stateful helper for tracking visited and queued URLs."""
    def __init__(self):
        self._seen: Set[str] = set()

    def add(self, url: str) -> bool:
        """
        Attempts to add normalized URL to set.
        Returns True if newly added, False if already seen.
        """
        try:
            norm = normalize_url(url)
            if norm in self._seen:
                return False
            self._seen.add(norm)
            return True
        except ValueError:
            return False

    def contains(self, url: str) -> bool:
        try:
            return normalize_url(url) in self._seen
        except ValueError:
            return False

    def size(self) -> int:
        return len(self._seen)
