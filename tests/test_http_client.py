"""
Tests for SafeHTTPClient safety rules and error handling.
"""

import unittest
from shared.http_client import SafeHTTPClient

class TestHTTPClient(unittest.TestCase):

    def test_http_client_rejects_unsafe_methods(self):
        client = SafeHTTPClient()

        with self.assertRaises(ValueError):
            client.fetch("https://example.com", method="POST")

        with self.assertRaises(ValueError):
            client.fetch("https://example.com", method="PUT")

        with self.assertRaises(ValueError):
            client.fetch("https://example.com", method="DELETE")

    def test_http_client_invalid_url_handling(self):
        client = SafeHTTPClient()
        resp = client.fetch("not-a-valid-url")

        self.assertFalse(resp.is_success)
        self.assertEqual(resp.status_code, 0)
        self.assertIn("Invalid URL", resp.error)

    def test_http_client_ssl_verification_default_enabled(self):
        import ssl
        client = SafeHTTPClient()
        self.assertTrue(client.verify_ssl)
        self.assertTrue(client._ssl_context.check_hostname)
        self.assertEqual(client._ssl_context.verify_mode, ssl.CERT_REQUIRED)

    def test_http_client_ssl_verification_can_be_disabled(self):
        import ssl
        client = SafeHTTPClient(verify_ssl=False)
        self.assertFalse(client.verify_ssl)
        self.assertFalse(client._ssl_context.check_hostname)
        self.assertEqual(client._ssl_context.verify_mode, ssl.CERT_NONE)

if __name__ == "__main__":
    unittest.main()
