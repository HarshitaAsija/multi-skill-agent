"""
Unit tests for Security, SSRF Prevention, Path Traversal, and Secret Redaction.
"""

import unittest
from shared.security import (
    is_safe_url,
    is_safe_output_path,
    mask_secrets,
    validate_runtime_bounds,
)
from shared.http_client import SafeHTTPClient


class TestSSRFPrevention(unittest.TestCase):
    """Verifies that malicious or internal addresses are blocked to prevent SSRF."""

    def test_cloud_metadata_blocked(self):
        safe, reason = is_safe_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(safe)
        self.assertIn("prohibited", reason.lower())

    def test_google_metadata_hostname_blocked(self):
        safe, reason = is_safe_url("http://metadata.google.internal/computeMetadata/v1/")
        self.assertFalse(safe)
        self.assertIn("prohibited", reason.lower())

    def test_localhost_and_loopback_blocked(self):
        safe, reason = is_safe_url("http://localhost:8080/admin")
        self.assertFalse(safe)

        safe, reason = is_safe_url("http://127.0.0.1:3000/")
        self.assertFalse(safe)

    def test_private_subnets_blocked_by_default(self):
        safe, _ = is_safe_url("http://10.0.0.1/internal")
        self.assertFalse(safe)

        safe, _ = is_safe_url("http://192.168.1.100/router")
        self.assertFalse(safe)

        safe, _ = is_safe_url("http://172.16.5.1/")
        self.assertFalse(safe)

    def test_private_subnets_allowed_when_flag_set(self):
        safe, _ = is_safe_url("http://192.168.1.100/", allow_private=True)
        self.assertTrue(safe)

    def test_dangerous_schemes_blocked(self):
        safe, _ = is_safe_url("file:///etc/passwd")
        self.assertFalse(safe)

        safe, _ = is_safe_url("gopher://127.0.0.1:70")
        self.assertFalse(safe)

        safe, _ = is_safe_url("javascript:alert(1)")
        self.assertFalse(safe)

    def test_legitimate_public_urls_allowed(self):
        safe, _ = is_safe_url("https://example.com/about")
        self.assertTrue(safe)

        safe, _ = is_safe_url("https://www.adobe.com/")
        self.assertTrue(safe)

    def test_http_client_blocks_ssrf_without_network_call(self):
        client = SafeHTTPClient()
        resp = client.fetch("http://169.254.169.254/secret")
        self.assertFalse(resp.is_success)
        self.assertIn("SSRF Protection", resp.error)


class TestPathTraversalProtection(unittest.TestCase):
    """Verifies protection against directory traversal attacks."""

    def test_null_byte_blocked(self):
        safe, _ = is_safe_output_path("report.json\x00.txt")
        self.assertFalse(safe)

    def test_empty_path_blocked(self):
        safe, _ = is_safe_output_path("")
        self.assertFalse(safe)

    def test_safe_local_paths_allowed(self):
        safe, resolved = is_safe_output_path("my-audit-report.md")
        self.assertTrue(safe)
        self.assertTrue(resolved.endswith("my-audit-report.md"))


class TestSecretRedaction(unittest.TestCase):
    """Verifies that API keys and secrets are masked from logs."""

    def test_mask_gemini_key(self):
        text = "Request sent with key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q"
        masked = mask_secrets(text)
        self.assertNotIn("A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q", masked)
        self.assertIn("AIzaSy***REDACTED***", masked)

    def test_mask_openai_key(self):
        text = "Calling OpenAI with sk-1234567890abcdefghijklmnopqrstuvwxyz"
        masked = mask_secrets(text)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", masked)
        self.assertIn("sk-***REDACTED***", masked)

    def test_mask_explicit_secret(self):
        text = "Internal token was MySuperSecretKey12345!"
        masked = mask_secrets(text, extra_secrets=["MySuperSecretKey12345!"])
        self.assertNotIn("MySuperSecretKey12345!", masked)
        self.assertIn("***REDACTED***", masked)


class TestRuntimeBoundsValidation(unittest.TestCase):
    """Verifies that input numbers are kept within safe operating limits."""

    def test_negative_or_excessive_pages_rejected(self):
        ok, _ = validate_runtime_bounds(max_pages=0, max_depth=2, timeout_seconds=10.0)
        self.assertFalse(ok)

        ok, _ = validate_runtime_bounds(max_pages=500, max_depth=2, timeout_seconds=10.0)
        self.assertFalse(ok)

    def test_excessive_depth_rejected(self):
        ok, _ = validate_runtime_bounds(max_pages=15, max_depth=20, timeout_seconds=10.0)
        self.assertFalse(ok)

    def test_valid_bounds_accepted(self):
        ok, _ = validate_runtime_bounds(max_pages=40, max_depth=4, timeout_seconds=10.0)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
