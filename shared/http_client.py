"""
Safe, Read-Only HTTP Client Foundation.
Implements GET and HEAD requests with retries, timeouts, polite delays, redirect tracking, and zero side-effects.
"""

import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from shared.config import (
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_POLITE_DELAY_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_USER_AGENT,
)
from shared.url_utils import normalize_url, is_valid_url

@dataclass
class HTTPResponse:
    url: str
    final_url: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    content_type: str = ""
    redirect_chain: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: Optional[str] = None
    is_success: bool = False

class SafeHTTPClient:
    """
    Polite, read-only HTTP client designed specifically for non-destructive website auditing.
    Only supports GET and HEAD methods.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        polite_delay: float = DEFAULT_POLITE_DELAY_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.polite_delay = polite_delay
        self.max_retries = max_retries
        self._last_request_time: float = 0.0

        # Permissive SSL context for auditing legacy or staging sites safely (read-only)
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    def _apply_polite_delay(self) -> None:
        """Enforces minimum polite delay between consecutive requests."""
        if self.polite_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.polite_delay:
                time.sleep(self.polite_delay - elapsed)

    def fetch(self, url: str, method: str = "GET") -> HTTPResponse:
        """
        Executes a safe GET or HEAD request.
        Raises ValueError if an unsafe method (POST/PUT/DELETE/etc) is passed.
        """
        method = method.upper()
        if method not in ("GET", "HEAD"):
            raise ValueError(f"Unsafe HTTP method '{method}' rejected. Auditor is strictly read-only (GET/HEAD only).")

        if not is_valid_url(url):
            return HTTPResponse(
                url=url,
                final_url=url,
                status_code=0,
                error=f"Invalid URL format: '{url}'",
                is_success=False
            )

        target_url = normalize_url(url)
        self._apply_polite_delay()

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "close",
        }

        retries = 0
        last_error: Optional[str] = None
        redirect_chain: List[str] = [target_url]

        class RedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                new_url = headers.get('Location')
                if new_url:
                    redirect_chain.append(new_url)
                return super().http_error_302(req, fp, code, msg, headers)
            http_error_301 = http_error_302
            http_error_303 = http_error_302
            http_error_307 = http_error_302
            http_error_308 = http_error_302

        opener = urllib.request.build_opener(
            RedirectHandler,
            urllib.request.HTTPSHandler(context=self._ssl_context)
        )

        while retries <= self.max_retries:
            start_time = time.time()
            try:
                req = urllib.request.Request(target_url, headers=headers, method=method)
                with opener.open(req, timeout=self.timeout) as resp:
                    elapsed = time.time() - start_time
                    self._last_request_time = time.time()

                    status_code = resp.getcode()
                    resp_headers = dict(resp.info())
                    content_type = resp_headers.get("Content-Type", "")

                    body = ""
                    if method == "GET":
                        # Read body up to 5MB max to prevent OOM on large files
                        raw_data = resp.read(5 * 1024 * 1024)
                        # Try decoding utf-8 with fallback
                        try:
                            body = raw_data.decode("utf-8", errors="replace")
                        except Exception:
                            body = raw_data.decode("latin-1", errors="replace")

                    final_url = resp.geturl()

                    return HTTPResponse(
                        url=target_url,
                        final_url=final_url,
                        status_code=status_code,
                        headers=resp_headers,
                        body=body,
                        content_type=content_type,
                        redirect_chain=redirect_chain,
                        elapsed_seconds=elapsed,
                        is_success=(200 <= status_code < 400)
                    )

            except urllib.error.HTTPError as e:
                elapsed = time.time() - start_time
                self._last_request_time = time.time()
                resp_headers = dict(e.headers) if e.headers else {}
                body = ""
                try:
                    body = e.read(512 * 1024).decode("utf-8", errors="replace")
                except Exception:
                    pass
                return HTTPResponse(
                    url=target_url,
                    final_url=e.url if hasattr(e, 'url') and e.url else target_url,
                    status_code=e.code,
                    headers=resp_headers,
                    body=body,
                    content_type=resp_headers.get("Content-Type", ""),
                    redirect_chain=redirect_chain,
                    elapsed_seconds=elapsed,
                    error=f"HTTP Error {e.code}: {e.reason}",
                    is_success=False
                )

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = str(e)
                retries += 1
                if retries <= self.max_retries:
                    time.sleep(0.5 * retries)  # Exponential backoff

        return HTTPResponse(
            url=target_url,
            final_url=target_url,
            status_code=0,
            redirect_chain=redirect_chain,
            error=f"Network request failed after {self.max_retries} retries: {last_error}",
            is_success=False
        )

    def head(self, url: str) -> HTTPResponse:
        """Executes a HEAD request."""
        return self.fetch(url, method="HEAD")
