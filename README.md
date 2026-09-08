# Agent Skill Marketplace — AI Readiness & On-Site Engagement Auditor

[![Adobe University Hackathon 2026](https://img.shields.io/badge/Adobe%20Hackathon-Round%203%20Submission-FF0000.svg)](https://github.com/HarshitaAsija/multi-skill-agent)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-63%20Passed-brightgreen.svg)](tests/)
[![Package Size](https://img.shields.io/badge/Package-110%20KB-success.svg)](agent-skill-marketplace-submission.zip)
[![Zero External APIs](https://img.shields.io/badge/External%20APIs-None-lightgrey.svg)](#)

---

## What This Is

Point it at any website URL and it automatically audits two things:

1. **AI Discoverability** — can AI search engines (ChatGPT, Perplexity, Claude) actually find, parse, and cite this site?
2. **On-Site Engagement** — once a visitor arrives (human or autonomous agent), does the page keep them?

It produces a structured JSON report plus an optional Markdown document with a 0–100 AI Readiness Score, a prioritized list of findings, ready-to-paste schema fixes, and a question gap analysis specific to the site's industry.

No API keys. No external ML services. No writes to any target. Just HTTP GET/HEAD requests and pure Python logic.

---

## Architecture

The system is split into four decoupled **agent skills** plus a shared module layer. Each skill does one focused job; the orchestrator stitches them together.

```
run_audit.py  (CLI entrypoint)
      |
      v
+------------------------------------------+
|           audit-orchestrator             |  <- declared entrypoint in marketplace.json
|  - URL normalization & robots gating     |
|  - Calls 3 specialist skills in sequence |
|  - Deduplicates & calibrates findings    |
|  - Computes AI Readiness Score (0-100)   |
|  - Runs Market Intelligence Engine       |
|  - Generates 5 proactive recommendations |
|  - Emits JSON + optional Markdown report |
+--------+-----------+--------------------+
         |           |           |
         v           v           v
+---------------+ +-----------+ +------------------+
| crawl-render  | | freshness | | engagement-audit |
|    -audit     | |  -corrobor| |                  |
|               | |   -ation  | | - Hero value     |
| - BFS crawl   | |           | |   proposition    |
|   up to 40 pg | | - Copyright| | - Form labels   |
| - robots.txt  | |   year     | | - CTA clarity   |
| - sitemap.xml | | - Timestamp| | - Breadcrumbs   |
| - /llms.txt   | |   staleness| | - FAQPage /     |
| - Schema.org  | | - Brand    | |   Speakable     |
| - DISC/KNOW   | |   title    | |   JSON-LD       |
|   checks      | |   suffix   | +------------------+
+---------------+ +-----------+

         Shared modules (common layer)
  models · config · http_client · severity
  evidence · url_utils · market_intelligence
  report_generator · report_validator
```

---

## The Four Skills

### `crawl-render-audit`
The crawl and extraction engine. Starts from the homepage and sitemap (if found), then walks outward using a **template-bucket BFS** — capping how many pages it samples per content type: homepage, about/company, product/pricing, docs/API, blog, and generic. This avoids accidentally scraping deep catalog pages while still covering the site's meaningful surface area.

A **180-second hard time budget** ensures the audit always finishes within the contest's 5-minute limit regardless of site size. On a typical site the crawl takes 20–40 seconds; the budget is a safety ceiling.

Each page goes through a `PageAnalyser` that extracts heading structure, Schema.org JSON-LD blocks, canonical/hreflang/OG tags, breadcrumbs, embedded objects (iframes, PDFs, `<object>` tags), text-to-HTML ratio, meta descriptions, and more. All extracted data feeds the DISC and KNOW check battery.

### `freshness-corroboration`
Dedicated to temporal and brand consistency. Parses copyright year text in footers, `<time>` elements, `article:published_time`/`article:modified_time` meta tags, and `datePublished` in JSON-LD. Flags stale years, contradictory date signals across content and footer, and checks whether the page title brand suffix is consistent across all crawled subpages.

### `engagement-audit`
Checks on-site experience from both a human and an autonomous agent perspective. Looks for a clear above-the-fold value proposition in the hero section, proper `<label>` associations for all form inputs, specific CTA button text (flags generics like "Click Here" or "Submit"), breadcrumb navigation on deep pages, and `FAQPage`/`Speakable` JSON-LD which lets AI assistants surface direct answers from the site.

### `audit-orchestrator`
The coordinator. Collects raw findings from all three specialists, strips per-URL suffixes from finding IDs, merges duplicates across pages, applies severity-weighted deductions to produce the AI Readiness Score, runs the Market Intelligence Engine, and appends five proactive recommendations that go beyond the flagged issues.

---

## Hero Feature: AI Answerability & Market Intelligence

Most audit tools stop at "you're missing schema." This engine goes a step further: it figures out what questions someone would realistically ask an AI assistant about this type of business, checks whether the current site content can actually answer those questions, and tells you exactly what to add — with copy-paste JSON-LD.

**How it works:**

1. **Industry Detection** — Scores the site against 10 verticals using Schema.org type matches (+4.0), URL path signals (+1.5), and text keywords (+0.8). Threshold ≥ 3.0 to claim a vertical; `General Business` is the universal fallback.
2. **Question Expectation Set** — Loads 5 representative questions a user or AI assistant would ask for that vertical.
3. **Answerability Test** — Checks whether the crawled content provides clear, extractable answers.
4. **Gap Report** — Surfaces unanswered questions as prioritized growth items with a suggested JSON-LD snippet.
5. **AI Query Simulation** — Generates a sample conversational prompt an AI assistant might receive about this site and flags the risk of a poor or hallucinated response.

**Supported verticals:**

| Vertical | Example gap questions |
|:---|:---|
| Restaurant & Dining | Opening hours, dietary options, table reservations |
| E-Commerce & Retail | Shipping fees, return policy, payment methods |
| SaaS / Tech | Pricing tiers, free trial, API docs, compliance (SOC2/GDPR) |
| Healthcare | Specialties, appointment booking, accepted insurance |
| Education | Degree programs, tuition, accreditation, online options |
| Real Estate | Available listings, tour scheduling, mortgage options |
| Legal | Practice areas, fee structure, bar admissions |
| Sports & Fitness | Equipment, class schedule, membership pricing |
| Food Delivery | Delivery radius, ETA, live tracking, missing item policy |
| General Business | Core services, quote channels, geographic coverage |

---

## Diagnostic Check Catalog

28 distinct checks across four categories. Findings carry a stable ID, a severity, an evidence snippet, and a suggested remediation.

### AI Discoverability — DISC

| ID | What it checks | Severity |
|:---|:---|:---|
| DISC-00 | Domain unreachable / DNS failure / connection timeout | CRITICAL |
| DISC-01 | AI scrapers blocked in `robots.txt` (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot) | HIGH |
| DISC-02 | Missing or unreachable XML sitemap | MEDIUM |
| DISC-03 | Sitemap entries missing `<lastmod>` timestamps | LOW |
| DISC-04 | Meta robots `noindex` blocking AI indexation | HIGH |
| DISC-05 | Missing or malformed `<link rel="canonical">` | LOW |
| DISC-06 | Missing OpenGraph / Twitter Card social metadata | LOW |
| DISC-07 | Client-side hydration lock — blank SPA mount with no SSR fallback | HIGH |
| DISC-08 | Missing `/llms.txt` machine-readable content index | MEDIUM |
| DISC-09 | Multilingual hreflang tags missing the `x-default` fallback directive | LOW |
| DISC-11 | Missing or suboptimal `<meta name="description">` (absent, < 40 chars, or > 320 chars) | MEDIUM |

### Machine & Agent Readiness — KNOW

| ID | What it checks | Severity |
|:---|:---|:---|
| KNOW-01 | Missing primary `<h1>` or broken heading hierarchy (e.g., h1 → h3 skip) | MEDIUM |
| KNOW-02 | Missing context-gated Schema.org JSON-LD (Organization, Product, Service) | HIGH |
| KNOW-03 | Comparative or tabular data rendered in unstructured layout markup | MEDIUM |
| KNOW-04 | Key information trapped in images without alt text | LOW |
| KNOW-05 | Missing `sameAs` entity authority links in Organization schema (Wikipedia, Wikidata, LinkedIn) | MEDIUM |
| KNOW-06 | Missing `BreadcrumbList` JSON-LD on subpages | LOW |
| KNOW-07 | Missing `Article` / `BlogPosting` schema on editorial pages | MEDIUM |
| KNOW-08 | Facts trapped in non-textual embedded elements — iframes, `<object>`, `<embed>`, PDFs | MEDIUM |

### Factual Freshness — FRESH

| ID | What it checks | Severity |
|:---|:---|:---|
| FRESH-01 | Outdated copyright year in footer text | MEDIUM |
| FRESH-02 | Stale article publication / modification timestamps | LOW |
| FRESH-03 | Contradictory year signals between content body and footer | MEDIUM |

### Brand Consistency — BRAND

| ID | What it checks | Severity |
|:---|:---|:---|
| BRAND-01 | Page title brand suffix inconsistent across crawled subpages | LOW |

### On-Site Engagement — ENG

| ID | What it checks | Severity |
|:---|:---|:---|
| ENG-01 | Missing above-the-fold hero value proposition | HIGH |
| ENG-02 | Form accessibility friction — inputs without `<label>` elements | MEDIUM |
| ENG-03 | Ambiguous CTA button labels ("Click Here", "Submit", "Go") | LOW |
| ENG-04 | Missing breadcrumb navigation on deep subpages | LOW |
| ENG-05 | No `FAQPage` or `Speakable` JSON-LD schema for AI answer engines | MEDIUM |

---

## AI Readiness Score

After finding deduplication, the orchestrator computes a single 0–100 score:

```
Score = max(0, 100 - sum of all deductions)
```

| Severity | Deduction | What it signals |
|:---|:---|:---|
| CRITICAL | −25 pts | Site is completely inaccessible to crawlers |
| HIGH | −15 pts | AI discovery or machine extraction is blocked |
| MEDIUM | −7 pts | Extractability or entity authority is degraded |
| LOW | −3 pts | Semantic hygiene is suboptimal but not blocking |

---

## Proactive Recommendations

Beyond diagnostic findings, the orchestrator always generates five proactive suggestions — things no automated check will flag but that meaningfully improve AI readiness:

1. **Semantic Anchor Pages** — Consolidate scattered topic content into single authoritative pages that AI retrievers can cite with confidence.
2. **Citation-Ready Fact Blocks** — Wrap key facts in `<dl>` / `<table>` markup so RAG pipelines can extract and chunk them cleanly.
3. **Entity Graph Disambiguation** — Add `sameAs` links to Wikidata and Wikipedia in Organization JSON-LD so AI knowledge graphs can anchor the entity's real-world identity.
4. **RAG Chunking Density** — Improve heading-to-text ratio so vector retrieval systems can split content at meaningful semantic boundaries.
5. **OpenAPI Action Manifest** — Expose a `/openapi.json` manifest so autonomous agents can discover and call the site's transactional capabilities (bookings, search, checkout) directly.

---

## Runtime & Constraints

| Property | Value |
|:---|:---|
| Pages crawled | Up to **40**, across 6 template buckets |
| Crawl depth | Up to **4 hops** from the root |
| Crawl time cap | **180 seconds** hard ceiling |
| Full audit time | **< 5 minutes** on a standard machine |
| HTTP operations | GET / HEAD only — strictly read-only |
| Runtime dependencies | `beautifulsoup4` only |
| External API calls | None |
| Package size | **~110 KB** (contest limit: 50 MB) |
| Test suite | **63 tests**, zero failures |

Crawler is polite by default: 0.25-second inter-request delay per host, `robots.txt` disallow rules respected, and per-template page caps to avoid deep catalog scraping.

---

## Installation & Usage

```bash
git clone https://github.com/HarshitaAsija/multi-skill-agent.git
cd multi-skill-agent
pip install -r requirements.txt
```

```bash
# Terminal executive summary (recommended for demos)
python run_audit.py --url https://example.com --summary

# Export a Markdown audit report
python run_audit.py --url https://example.com --markdown report.md --summary

# Structured JSON output
python run_audit.py --url https://example.com --output report.json
```

**CLI flags:**

| Flag | Description | Default |
|:---|:---|:---|
| `--url` | Target website URL *(required)* | — |
| `--summary` | Print formatted terminal executive summary | `false` |
| `--markdown` | Write Markdown audit report to a file | `none` |
| `--output` | Write JSON report to a file (stdout if omitted) | stdout |
| `--max-pages` | Maximum pages to crawl | `40` |
| `--max-depth` | Maximum link depth from root | `4` |
| `--timeout` | Per-request HTTP timeout in seconds | `10.0` |

---

## Running Tests

```bash
python -m pytest tests/ -q
# or
python -m unittest discover tests
```

Expected: `63 passed` in under 10 seconds.

---

## Validating the Submission Package

```bash
python scripts/package_submission.py
```

Runs all 63 tests, validates `marketplace.json` and all `SKILL.md` files against the agentskills.io schema, builds the submission zip, checks the archive is under 50 MB, and does a standalone CLI smoke test from the unpacked archive. All four steps must show `[PASS]`.
