"""
Tests for robots.txt parser and AI User-Agent block detection.
"""

import unittest
from skills import load_skill_module

robots_mod = load_skill_module("crawl-render-audit", "robots_parser.py")
RobotsParser = robots_mod.RobotsParser
RobotsParseResult = robots_mod.RobotsParseResult

SAMPLE_ROBOTS_TXT = """
# Sample robots.txt
User-agent: *
Disallow: /admin/
Disallow: /private/

User-agent: GPTBot
Disallow: /

User-agent: PerplexityBot
Disallow: /

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap_index.xml
"""

class TestRobotsParser(unittest.TestCase):

    def test_parse_rules_and_sitemaps(self):
        parser = RobotsParser()
        rules, sitemaps = parser._parse(SAMPLE_ROBOTS_TXT)

        self.assertIn("gptbot", rules)
        self.assertIn("perplexitybot", rules)
        self.assertIn("*", rules)
        self.assertEqual(len(sitemaps), 2)
        self.assertEqual(sitemaps[0], "https://example.com/sitemap.xml")

    def test_ai_agent_blocked_detection(self):
        parser = RobotsParser()
        rules, sitemaps = parser._parse(SAMPLE_ROBOTS_TXT)
        res = RobotsParseResult(
            robots_url="https://example.com/robots.txt",
            http_status=200,
            raw_content=SAMPLE_ROBOTS_TXT,
            is_accessible=True,
            rules=rules,
            sitemap_urls=sitemaps
        )

        blocked = res.get_blocked_ai_agents()
        self.assertIn("GPTBot", blocked)
        self.assertIn("PerplexityBot", blocked)
        self.assertNotIn("ClaudeBot", blocked)

    def test_path_allow_disallow_logic(self):
        parser = RobotsParser()
        rules, sitemaps = parser._parse(SAMPLE_ROBOTS_TXT)
        res = RobotsParseResult(
            robots_url="https://example.com/robots.txt",
            http_status=200,
            raw_content=SAMPLE_ROBOTS_TXT,
            is_accessible=True,
            rules=rules,
            sitemap_urls=sitemaps
        )

        self.assertFalse(res.is_path_allowed("/admin/dashboard", user_agent="*"))
        self.assertTrue(res.is_path_allowed("/public/about", user_agent="*"))

if __name__ == "__main__":
    unittest.main()
