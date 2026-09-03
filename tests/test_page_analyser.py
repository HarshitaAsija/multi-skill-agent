"""
Tests for HTML Page Analyser and Signal Extractor.
"""

import unittest
from skills import load_skill_module

analyser_mod = load_skill_module("crawl-render-audit", "page_analyser.py")
PageAnalyser = analyser_mod.PageAnalyser

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Enterprise AI Automation Platform | Acme Corp</title>
    <meta name="description" content="Acme Corp provides automated AI readiness auditing for enterprises.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://example.com/">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Acme Corp",
        "url": "https://example.com"
    }
    </script>
</head>
<body>
    <header>
        <nav aria-label="Main Navigation">
            <a href="/">Home</a>
            <a href="/pricing">Pricing</a>
            <a href="/about">About</a>
        </nav>
    </header>
    <main>
        <h1>Automate Your AI Readiness Today</h1>
        <p>Our platform audits your website for agent discoverability and RAG readiness.</p>
        <h3>Skipped Heading Level</h3>
        <table id="pricing-table">
            <tr><th>Plan</th><th>Price</th></tr>
            <tr><td>Enterprise</td><td>$999</td></tr>
        </table>
        <img src="/hero.png">
        <button class="btn-primary">Start Free Trial</button>
    </main>
    <footer>
        <p>© 2026 Acme Corp. All rights reserved.</p>
    </footer>
</body>
</html>
"""

class TestPageAnalyser(unittest.TestCase):

    def test_page_signal_extraction(self):
        analyser = PageAnalyser()
        data = analyser.analyse("https://example.com/", SAMPLE_HTML)

        self.assertEqual(data.title, "Enterprise AI Automation Platform | Acme Corp")
        self.assertEqual(data.meta_description, "Acme Corp provides automated AI readiness auditing for enterprises.")
        self.assertEqual(data.meta_robots, "index, follow")
        self.assertEqual(data.canonical_url, "https://example.com/")
        self.assertTrue(data.has_h1)
        self.assertEqual(data.h1_tags[0], "Automate Your AI Readiness Today")
        self.assertIn("H1 -> H3", data.heading_level_skips)
        self.assertTrue(data.has_nav_landmark)
        self.assertTrue(data.has_main_landmark)
        self.assertTrue(data.has_tabular_data)
        self.assertIn("Organization", data.json_ld_types)
        self.assertEqual(data.images_missing_alt_count, 1)
        self.assertIn("Start Free Trial", data.button_cta_labels)
        self.assertIn("© 2026 Acme Corp", data.footer_text)

    def test_empty_og_image_content(self):
        """Edge case: og:image with empty content='' should not populate open_graph data."""
        html = '''
        <html><head>
            <meta property="og:title" content="Hello">
            <meta property="og:image" content="">
            <meta property="og:description" content="   ">
        </head><body></body></html>
        '''
        analyser = PageAnalyser()
        data = analyser.analyse("https://test.com", html)
        self.assertEqual(data.open_graph.get("og:title"), "Hello")
        self.assertNotIn("og:image", data.open_graph)
        self.assertNotIn("og:description", data.open_graph)

if __name__ == "__main__":
    unittest.main()
