"""
Tests for URL utilities: normalization, validation, domain extraction, deduplication.
"""

import unittest
from shared.url_utils import (
    is_valid_url,
    normalize_url,
    get_domain,
    is_same_domain,
    resolve_relative_url,
    URLDeduplicator
)

class TestURLUtils(unittest.TestCase):

    def test_is_valid_url(self):
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://sub.example.co.uk/path?q=1"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url("invalid-url"))
        self.assertFalse(is_valid_url(""))
        self.assertFalse(is_valid_url(None))

    def test_normalize_url(self):
        self.assertEqual(normalize_url("HTTPS://EXAMPLE.COM/Page"), "https://example.com/Page")
        self.assertEqual(normalize_url("http://example.com:80/foo"), "http://example.com/foo")
        self.assertEqual(normalize_url("https://example.com:443/bar"), "https://example.com/bar")
        self.assertEqual(normalize_url("https://example.com/path#section"), "https://example.com/path")
        self.assertEqual(normalize_url("https://example.com/?b=2&a=1"), "https://example.com/?a=1&b=2")
        self.assertEqual(normalize_url("https://example.com"), "https://example.com/")

    def test_invalid_url_normalization_raises(self):
        with self.assertRaises(ValueError):
            normalize_url("not-a-url")

    def test_domain_extraction(self):
        self.assertEqual(get_domain("https://subdomain.example.org:8080/path"), "subdomain.example.org")
        self.assertTrue(is_same_domain("https://example.com/a", "http://example.com/b"))
        self.assertFalse(is_same_domain("https://example.com", "https://other.com"))

    def test_resolve_relative_url(self):
        self.assertEqual(resolve_relative_url("https://example.com/docs/", "../about"), "https://example.com/about")
        self.assertIsNone(resolve_relative_url("https://example.com/", "javascript:void(0)"))

    def test_url_deduplicator(self):
        dedup = URLDeduplicator()
        self.assertTrue(dedup.add("https://example.com/a#hash"))
        self.assertFalse(dedup.add("https://EXAMPLE.COM/a"))
        self.assertEqual(dedup.size(), 1)

if __name__ == "__main__":
    unittest.main()
