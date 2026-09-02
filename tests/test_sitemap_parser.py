"""
Tests for sitemap.xml parser.
"""

import unittest
from skills import load_skill_module

sitemap_mod = load_skill_module("crawl-render-audit", "sitemap_parser.py")
SitemapParser = sitemap_mod.SitemapParser

SAMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://example.com/</loc>
      <lastmod>2026-01-15</lastmod>
      <priority>1.0</priority>
   </url>
   <url>
      <loc>https://example.com/pricing</loc>
      <lastmod>2026-02-01</lastmod>
      <priority>0.8</priority>
   </url>
   <url>
      <loc>https://example.com/about</loc>
      <priority>0.5</priority>
   </url>
</urlset>
"""

class TestSitemapParser(unittest.TestCase):

    def test_parse_urlset_xml(self):
        parser = SitemapParser()
        entries = parser._parse_xml(SAMPLE_SITEMAP_XML, root_url="https://example.com", current_url="https://example.com/sitemap.xml", depth=0)

        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].url, "https://example.com/")
        self.assertEqual(entries[0].lastmod, "2026-01-15")
        self.assertEqual(entries[0].priority, 1.0)
        self.assertEqual(entries[1].url, "https://example.com/pricing")
        self.assertEqual(entries[1].priority, 0.8)

if __name__ == "__main__":
    unittest.main()
