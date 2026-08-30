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

if __name__ == "__main__":
    unittest.main()
