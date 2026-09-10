# Agent Skill Marketplace — AI Readiness & On-Site Engagement Auditor

[![Adobe University Hackathon 2026](https://img.shields.io/badge/Adobe%20Hackathon-Round%203%20Submission-FF0000.svg)](https://github.com/HarshitaAsija/multi-skill-agent)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-86%20Passed-brightgreen.svg)](tests/)
[![Package Size](https://img.shields.io/badge/Package-125%20KB-success.svg)](agent-skill-marketplace-submission.zip)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Google%20Gemini%202.5%20Flash-4285F4.svg)](#)
[![Security](https://img.shields.io/badge/Security-SSRF%20%26%20Secret%20Hardened-brightgreen.svg)](#)

---

## What This Is

Point it at any website URL and it automatically audits two things:

1. **AI Discoverability** — can AI search engines (ChatGPT, Perplexity, Claude, Gemini) actually find, parse, understand, and cite this site?
2. **On-Site Engagement** — once a visitor arrives (human or autonomous agent), does the page retain them and enable action?

It produces a structured JSON report plus an optional Markdown document with a 0–100 AI Readiness Score, a prioritized list of technical findings, ready-to-paste schema fixes, and deep question gap analysis.

Powered by **Google Gemini 2.5 Flash** for real semantic content evaluation and site-tailored recommendations, with zero heavy external packages — built purely using Python standard library HTTP calling Google's REST API.

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
|  - Invokes Google Gemini 2.5 Flash       |
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
  evidence · url_utils · gemini_client
  security · market_intelligence · report_generator
```

---

## Production Hardening & Security Architecture

This project was built from the ground up with strict defense-in-depth security:

| Security Domain | Protection Mechanism |
|:---|:---|
| **SSRF Defense** | Target URLs and redirects are validated against private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`), `localhost`, and cloud instance metadata endpoints (`169.254.169.254`, `metadata.google.internal`). Internal LAN probing is blocked by default. |
| **Secret Protection** | Zero hardcoded keys in source code. `.env` and credential files are strictly ignored in `.gitignore`. Gemini API calls send credentials via `x-goog-api-key` HTTP headers (never leaked into query parameters, URLs, or proxy logs). |
| **Log Sanitization** | `SecretRedactionFilter` intercepts all log records to redact API keys and bearer tokens (`mask_secrets()`). |
| **Path Traversal Protection** | File export flags (`--output`, `--markdown`) sanitize paths, reject null-byte injections, and prohibit writes to sensitive system roots. |
| **Input Boundary Validation** | Enforces strict bounds on crawl parameters (`max_pages` 1–200, `max_depth` 1–10, `timeout` 1–60s) preventing resource exhaustion or DoS. |
| **Safe Error Handling** | Production CLI suppresses raw tracebacks and displays clear error messages without exposing system internals (verbose tracebacks gated behind `--debug`). |
| **Strictly Read-Only** | Only HTTP `GET` and `HEAD` methods are implemented. No forms are submitted, no state is mutated, and zero destructive actions are executed. |

---

## The Four Skills

### `crawl-render-audit`
The crawl and extraction engine. Starts from the homepage and sitemap (if found), then walks outward using a **template-bucket BFS** — capping how many pages it samples per content type: homepage, about/company, product/pricing, docs/API, blog, and generic. This avoids accidentally scraping deep catalog pages while still covering the site's meaningful surface area.

A **180-second hard time budget** ensures the audit always finishes within the contest's 5-minute limit regardless of site size. On a typical site the crawl takes 20–40 seconds; the budget is a safety ceiling.

Each page goes through a `PageAnalyser` that extracts heading structure, Schema.org JSON-LD blocks, canonical/hreflang/OG tags, breadcrumbs, embedded objects (iframes, PDFs, `<object>` tags), text-to-HTML ratio, meta descriptions, and visible body text. All extracted data feeds the DISC and KNOW check battery.

### `freshness-corroboration`
Dedicated to temporal and brand consistency. Parses copyright year text in footers, `<time>` elements, `article:published_time`/`article:modified_time` meta tags, and `datePublished` in JSON-LD. Flags stale years, contradictory date signals across content and footer, and checks whether the page title brand suffix is consistent across all crawled subpages.

### `engagement-audit`
Checks on-site experience from both a human and an autonomous agent perspective. Looks for a clear above-the-fold value proposition in the hero section, proper `<label>` associations for all form inputs, specific CTA button text (flags generics like "Click Here" or "Submit"), breadcrumb navigation on deep pages, and `FAQPage`/`Speakable` JSON-LD which lets AI assistants surface direct answers from the site.

### `audit-orchestrator`
The coordinator. Collects raw findings from all three specialists, strips per-URL suffixes from finding IDs, merges duplicates across pages, applies severity-weighted deductions to produce the AI Readiness Score, and executes the Market Intelligence & Gemini reasoning pipeline.

---

## Dual-Engine Intelligence: Google Gemini 2.5 Flash + Deterministic Heuristics

The system combines real LLM semantic reasoning with rigorous structural diagnostics:

| Feature | Powered by Google Gemini (`GEMINI_API_KEY`) | Offline Fallback (Keyless Mode) |
|:---|:---|:---|
| **Question Answerability** | Reads real extracted website text and reasons whether Perplexity / ChatGPT can verify each fact. | Pattern matching against domain regex and keyword matrices. |
| **Evidence Extraction** | Quotes concrete excerpts from the site's actual body copy or explains specifically what details are missing. | Identifies matching DOM tokens and text substrings. |
| **Proactive Recommendations** | Dynamically synthesizes 4-5 high-impact architectural recommendations tailored specifically to that brand. | Calibrated forward-looking standard recommendations. |
| **Executive Synthesis** | Generates an executive assessment of the brand's AI search stance and conversion vulnerabilities. | Structured severity scorecard and metric breakdowns. |
| **FAQ Schema Generation** | Generates tailored Schema.org JSON-LD with real information from the website. | Structured FAQ templates aligned to detected industry. |

**Zero Heavy Dependencies:** The Gemini client is built entirely using Python's standard library `urllib.request` and `json`. No external SDKs (like `google-generativeai` or `langchain`) are needed. This keeps the package size at just **~120 KB** (well under the 50 MB limit) while delivering full LLM capability.

---

## Supported Industry Verticals (Market Intelligence)

The engine automatically detects the business domain across 10 verticals:

| Vertical | High-Intent Question Gaps Evaluated |
|:---|:---|
| **Restaurant & Dining** | Opening hours, dietary/vegetarian options, online table reservations, physical location, menu details. |
| **E-Commerce & Retail** | Product pricing, shipping destinations & delivery times, return & refund policies, checkout payment methods, order tracking. |
| **SaaS / Technology** | Subscription pricing tiers, free trial availability, platform integrations, public API documentation, security & compliance (SOC2/GDPR). |
| **Healthcare & Medical** | Medical specialties, online appointment booking, accepted insurance plans, clinic hours, doctor board certifications. |
| **Education & Academy** | Degree programs, admission requirements, tuition & financial aid, accreditation, online/hybrid delivery. |
| **Real Estate** | Available listings, tour scheduling, geographic coverage, mortgage financing options, broker licensing. |
| **Legal & Law Services** | Practice areas, consultation intake channels, fee structures (contingency/hourly), state bar admissions, past settlements. |
| **Sports & Fitness** | Equipment & amenities, group class schedules, membership pricing & trial passes, trainer certifications, operating hours. |
| **Food Delivery** | Delivery postal radius, delivery ETA & fees, live order tracking, packaging safety, missing item resolution. |
| **General Business** | Core service offerings, target audience personas, quote request channels, geographic coverage, client testimonials & case studies. |

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

## Runtime & Constraints

| Property | Value |
|:---|:---|
| Pages crawled | Up to **40**, across 6 template buckets |
| Crawl depth | Up to **4 hops** from the root |
| Crawl time cap | **180 seconds** hard ceiling |
| Full audit time | **< 5 minutes** on a standard machine |
| HTTP operations | GET / HEAD only — strictly read-only |
| Runtime dependencies | `beautifulsoup4` only |
| External packages | None (Gemini API called via Python standard library) |
| Package size | **~120 KB** (contest limit: 50 MB) |
| Test suite | **69 tests**, zero failures |

---

## Installation & Usage

```bash
git clone https://github.com/HarshitaAsija/multi-skill-agent.git
cd multi-skill-agent
pip install -r requirements.txt
```

### Setting Up Google Gemini (Optional but Recommended)

You can get a free Gemini API key from [aistudio.google.com](https://aistudio.google.com).

```bash
# Option 1: Export environment variable
export GEMINI_API_KEY="AIzaSyYourKeyHere..."

# Option 2: Put it in a local .env file
echo "GEMINI_API_KEY=AIzaSyYourKeyHere..." > .env

# Option 3: Pass via CLI argument
python run_audit.py --url https://example.com --summary --gemini-api-key "AIzaSyYourKeyHere..."
```

*(If no key is provided, the tool automatically runs in deterministic offline mode with zero errors.)*

### Running Audits

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
| `--gemini-api-key` | Google Gemini API Key for LLM reasoning | `None` (reads env) |
| `--allow-private` | Permit auditing private/loopback IPs (disabled by default for SSRF safety) | `false` |
| `--debug` | Enable verbose debugging stack traces | `false` |
| `--max-pages` | Maximum pages to crawl (1–200) | `40` |
| `--max-depth` | Maximum link depth from root (1–10) | `4` |
| `--timeout` | Per-request HTTP timeout in seconds (1.0–60.0s) | `10.0` |

---

## Running Tests

```bash
python -m pytest tests/ -q
# or
python -m unittest discover tests
```

Expected: `86 passed` in under 5 seconds.

---

## Validating the Submission Package

```bash
python scripts/package_submission.py
```

Runs all 86 tests, validates `marketplace.json` and all `SKILL.md` files against the agentskills.io schema, builds the submission zip, checks the archive is under 50 MB, and does a standalone CLI smoke test from the unpacked archive. All four steps must show `[PASS]`.
