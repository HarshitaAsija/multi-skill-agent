"""
URL Parsing, Validation, and Normalization Utilities.
"""

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, urljoin
import re
import ipaddress
from typing import Optional, Set, Tuple

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

def is_safe_url(url: str, allow_private: bool = False) -> Tuple[bool, str]:
    """
    Validates URL safety against SSRF (Server-Side Request Forgery) attacks.
    Blocks:
      - Non-HTTP/HTTPS schemes (file://, gopher://, etc.)
      - Localhost and loopback addresses (127.0.0.0/8, ::1)
      - Link-local and cloud instance metadata services (169.254.169.254, metadata.google.internal)
      - Private RFC-1918 subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) unless allow_private=True
    """
    if not is_valid_url(url):
        return False, "Invalid URL format or unsupported scheme"

    parsed = urlparse(url.strip())
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
        if hostname_lower == "localhost" or hostname_lower.endswith(".localhost") or hostname_lower.endswith(".local"):
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
    """
    Checks whether two URLs share the same domain / host.
    Applies conservative apex <-> www symmetry:
    'example.com' and 'www.example.com' are treated as the same domain.
    Does not allow arbitrary cross-subdomain traversal without PSL awareness.
    """
    d1 = get_domain(url1)
    d2 = get_domain(url2)
    if not d1 or not d2:
        return False
    if d1 == d2:
        return True
    if d1.startswith("www.") and d1[4:] == d2:
        return True
    if d2.startswith("www.") and d2[4:] == d1:
        return True
    return False

def get_host_alias(url: str) -> Optional[str]:
    """
    Generates the counterpart host alias URL:
    - 'example.com' -> 'www.example.com'
    - 'www.example.com' -> 'example.com'
    Preserves scheme, path, query, and port. Returns None if host cannot be aliased.
    """
    if not is_valid_url(url):
        return None
    parsed = urlparse(url.strip())
    host = parsed.hostname or ""
    if not host:
        return None

    # Determine counterpart host
    if host.lower().startswith("www."):
        alias_host = host[4:]
    else:
        alias_host = f"www.{host}"

    # Reconstruct netloc with original port if present
    netloc = alias_host
    if parsed.port:
        netloc = f"{alias_host}:{parsed.port}"

    return urlunparse((parsed.scheme, netloc, parsed.path or "/", parsed.params, parsed.query, parsed.fragment))

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
