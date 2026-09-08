# Agent Skill Marketplace: AI Readiness & On-Site Engagement Auditor

[![Adobe University Hackathon 2026](https://img.shields.io/badge/Adobe%20Hackathon-Round%203%20Submission-FF0000.svg)](https://github.com/HarshitaAsija/multi-skill-agent)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-63%20Passed-brightgreen.svg)](tests/)
[![Package Size](https://img.shields.io/badge/Package%20Size-~93%20KB-success.svg)](marketplace.json)

## Overview
The **Agent Skill Marketplace** is a lightweight, non-destructive, highly generalizable website auditing engine built for **Adobe University Hackathon 2026 (Round 3)**.

It evaluates any website URL across five core dimensions:
1. **AI Discoverability**: Why AI search engines (Perplexity, SearchGPT, ChatGPT) and autonomous machine crawlers may fail to find, parse, or cite content (including `robots.txt` AI blocks, XML sitemaps, and the modern `/llms.txt` standard).
2. **Machine/Agent Readiness & Entity Authority**: Structured schema completeness (Schema.org / JSON-LD), `sameAs` entity authority links (Wikipedia, LinkedIn, Wikidata), and client-side JavaScript hydration locks.
3. **Factual Freshness & Brand Consistency**: Outdated copyright timestamps, stale temporal signals, and cross-page brand suffix consistency (`<title>` tag alignment).
4. **On-Site Engagement & Conversational Hooks**: Above-the-fold value proposition clarity, navigation hierarchy, subpage context retention, CTA clarity, and `FAQPage`/`Speakable` schema eligibility.
5. **AI Answerability & Market Intelligence (Hero Feature)**: Industry-specific Question Gap Analysis comparing what conversational AI assistants *should* be able to answer vs. what the website currently answers, with an automated **Smart Growth Roadmap** and ready-to-paste schema remediations.

---

## Skill Architecture

The marketplace consists of four decoupled modular skills orchestrated by a central coordinator:

| Skill Name | Role | Description |
| :--- | :--- | :--- |
| **`audit-orchestrator`** | **Designated Entrypoint** | Primary coordinator declared in `marketplace.json`. Coordinates specialist skills, deduplicates findings, calculates the **AI Readiness Score (0-100)**, runs Market Intelligence, and emits validated JSON/Markdown reports. |
| **`crawl-render-audit`** | Specialist Skill | Audits HTTP accessibility, `robots.txt` AI agent directives, `sitemap.xml`, `/llms.txt` existence, template-bucket BFS crawling, client-side hydration locks, and Schema.org entity authority. |
| **`freshness-corroboration`** | Specialist Skill | Audits temporal freshness signals, copyright recency, publication timestamps, and cross-page brand title consistency (`BRAND-01`). |
| **`engagement-audit`** | Specialist Skill | Audits on-site human/agent engagement: hero value propositions, form friction, CTA ambiguity, breadcrumb context, and `FAQPage`/`Speakable` schema presence (`ENG-05`). |

---

## Hero Feature: AI Answerability & Market Intelligence Engine

Most audit tools only tell you what is technically broken (e.g. *"Missing schema"*). Our **Answerability Engine** bridges technical auditing to real business growth:

```
                  Target Website URL
                          ↓
              Detect Industry Vertical
      (Restaurant, E-Commerce, SaaS, Healthcare, Education, General Business)
                          ↓
       ┌──────────────────┴──────────────────┐
       ↓                                     ↓
AI Answerability Test               Market Question Expectation
What can AI assistants answer       What do users & AI expect
from your current content?          for this type of business?
       ↓                                     ↓
       └──────────────────┬──────────────────┘
                          ↓
              QUESTION GAP ANALYSIS
        (e.g., 4 / 5 Answerable = 80% Market Coverage)
                          ↓
           SIMULATED AI QUERY PROMPT & RISKS
      ("Does Bistro offer vegetarian options?" -> High Risk)
                          ↓
            SMART GROWTH ROADMAP (PRIORITIZED)
     (Priority 1, 2, 3... ranked by Impact and Dev Effort)
                          ↓
           READY-TO-PASTE FAQ SCHEMA CODE BLOCKS
```

### Supported Industry Verticals:
- **Restaurant & Dining**: Opening hours, physical address, menu items, vegetarian/dietary options, table reservations.
- **E-Commerce & Retail**: Product pricing, shipping fees & delivery times, return/refund policy, payment methods, order tracking.
- **Software & Technology (SaaS)**: Subscription pricing tiers, free trial/demo availability, platform integrations, public API docs, security & compliance (SOC2/GDPR).
- **Healthcare & Medical**: Medical specialties, online appointment booking, accepted insurance, clinic hours & accessibility, doctor board certifications.
- **Education & Academy**: Academic degree programs, admission requirements & deadlines, tuition & financial aid, institutional accreditation, online/hybrid classes.
- **Real Estate & Property**: Available listings & units, geographic coverage areas, tour & viewing scheduling, pricing & mortgage options, broker licensing.
- **Legal & Law Services**: Practice areas & specialties, confidential consultation intake, fee structures (contingency/hourly), state bar admissions, verdicts & settlements.
- **Sports, Fitness & Gym**: Training equipment & amenities, group fitness schedule, membership pricing & trial passes, operating hours, certified trainer credentials.
- **Food Delivery & Cloud Kitchen**: Delivery coverage radius & postal codes, delivery ETA & fees, online ordering & live tracking, packaging safety, missing item resolution.
- **General Business & Services (Universal Fallback)**: Core service offerings, target audience personas, quote request channels, geographic service areas, client testimonials & case studies.

---

## Safety & Runtime Constraints
- **Strictly Read-Only**: Performs HTTP GET and HEAD requests only. Never authenticates, submits forms, or executes POST/PUT/DELETE operations.
- **Zero External API Costs & 100% Deterministic**: Operates entirely offline without requiring OpenAI, Claude, or third-party LLM API keys. Runs fast and deterministically.
- **Ultra-Lightweight**: Entire package is **~93 KB** (the contest limit is 50 MB). Completes full audits in **under 15 seconds** (contest limit is 5 minutes).
- **Polite & Robots-Compliant**: Enforces respectful host delay, obeys `robots.txt` disallows, and samples across 5 template buckets rather than scraping deep catalogs indiscriminately.

---

## Installation & Setup

```bash
# Clone repository
git clone https://github.com/HarshitaAsija/multi-skill-agent.git
cd multi-skill-agent

# Install lightweight dependency (only beautifulsoup4 is required)
pip install -r requirements.txt
```

---

## Local Testing Guide

### Step 1 — Run an Audit on Any Website

```bash
# Option A: Formatted executive summary in terminal (recommended for demos)
python run_audit.py --url https://example.com --summary

# Option B: Export publication-ready Markdown report (Scorecard, Question Gaps & FAQ Schema)
python run_audit.py --url https://example.com --markdown audit-report.md --summary

# Option C: Full structured JSON report to stdout or file
python run_audit.py --url https://example.com --output report.json
```

### Step 2 — Run the Automated Test Suite

```bash
python -m unittest discover tests
```

Expected output:
```
Ran 63 tests in ~1.6s
OK
```

### Step 3 — Build & Validate the Submission Package

```bash
python scripts/package_submission.py
```

This automated validator:
1. Executes all **63 unit tests** with zero failures.
2. Validates `marketplace.json` schema and agentskills.io compliance for every `SKILL.md`.
3. Creates a clean, compressed submission archive (`agent-skill-marketplace-submission.zip`).
4. Verifies the archive size is strictly under 50 MB (~110 KB).
5. Unpacks the archive into an isolated temporary directory and confirms standalone CLI execution.

---

## CLI Options Reference

| Flag | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--url` | `-u` | Target website URL to audit *(Required)* | *(None)* |
| `--summary` | `-s` | Display formatted terminal executive summary & Question Gaps | `False` |
| `--markdown` | `-m` | Export publication-ready Markdown audit document | `None` |
| `--output` | `-o` | Save structured JSON report to a file path | `None` (stdout) |
| `--max-pages` | `-p` | Maximum pages to sample across template buckets | `40` |
| `--max-depth` | `-d` | Maximum crawl link depth | `4` |
| `--timeout` | `-t` | Per-request HTTP timeout in seconds | `10.0` |

---

## Comprehensive Diagnostic Check Catalog

| Check ID | Skill Module | Category | Description | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **`DISC-00`** | `crawl-render-audit` | AI Discoverability | Target Domain Unreachable / DNS / Connection Timeout | CRITICAL |
| **`DISC-01`** | `crawl-render-audit` | AI Discoverability | AI Scraper User-Agents Blocked in `robots.txt` (GPTBot, ClaudeBot, etc.) | HIGH |
| **`DISC-02`** | `crawl-render-audit` | AI Discoverability | Missing or Unreachable XML Sitemap | MEDIUM |
| **`DISC-03`** | `crawl-render-audit` | AI Discoverability | Sitemap Lacks Content Modification Timestamps (`<lastmod>`) | LOW |
| **`DISC-04`** | `crawl-render-audit` | AI Discoverability | Meta Robots AI Tag Restricting Indexation (`noindex`) | HIGH |
| **`DISC-05`** | `crawl-render-audit` | AI Discoverability | Missing or Malformed `<link rel="canonical">` Tag | LOW |
| **`DISC-06`** | `crawl-render-audit` | AI Discoverability | Missing OpenGraph / Twitter Card Social Metadata | LOW |
| **`DISC-07`** | `crawl-render-audit` | Machine Readiness | Client-Side Hydration Lock (Blank SPA Mount Container) | HIGH |
| **`DISC-08`** | `crawl-render-audit` | AI Discoverability | Missing `/llms.txt` Machine-Readable Content Index | MEDIUM |
| **`DISC-09`** | `crawl-render-audit` | AI Discoverability | Multilingual Hreflang Tags Missing `x-default` Fallback Directive | LOW |
| **`DISC-11`** | `crawl-render-audit` | AI Discoverability | Missing or Suboptimal Snippet Summary Metadata (`<meta name="description">`) | MEDIUM |
| **`KNOW-01`** | `crawl-render-audit` | Machine Readiness | Missing Primary `<H1>` Heading or Broken Heading Hierarchy | MEDIUM |
| **`KNOW-02`** | `crawl-render-audit` | Machine Readiness | Missing Context-Gated Schema.org JSON-LD (Organization, Product) | HIGH |
| **`KNOW-03`** | `crawl-render-audit` | Machine Readiness | Comparative / Tabular Data in Unstructured Layout Markup | MEDIUM |
| **`KNOW-04`** | `crawl-render-audit` | Machine Readiness | Key Information Trapped in Images (Missing Alt Text) | LOW |
| **`KNOW-05`** | `crawl-render-audit` | Machine Readiness | Missing `sameAs` Entity Authority Links in Organization Schema | MEDIUM |
| **`KNOW-06`** | `crawl-render-audit` | Machine Readiness | Missing `BreadcrumbList` Schema.org Structured Data on Subpage | LOW |
| **`KNOW-07`** | `crawl-render-audit` | Machine Readiness | Missing `Article` / `BlogPosting` Schema.org Markup on Editorial Page | MEDIUM |
| **`KNOW-08`** | `crawl-render-audit` | Machine Readiness | Key Information Trapped in Non-Textual Embedded Elements (Iframe/Object/PDF) | MEDIUM |
| **`FRESH-01`** | `freshness-corroboration` | Factual Freshness | Outdated Copyright Year Detected in Footer Text | MEDIUM |
| **`FRESH-02`** | `freshness-corroboration` | Factual Freshness | Stale Article Publication / Modification Timestamps | LOW |
| **`FRESH-03`** | `freshness-corroboration` | Factual Freshness | Contradictory Year Signals Between Content and Footer | MEDIUM |
| **`BRAND-01`** | `freshness-corroboration` | Factual Freshness | Page Title Brand Suffix Inconsistency Across Subpages | LOW |
| **`ENG-01`** | `engagement-audit` | Onsite Engagement | Missing Above-the-Fold Hero Value Proposition | HIGH |
| **`ENG-02`** | `engagement-audit` | Onsite Engagement | Form Accessibility Friction (Inputs Missing `<label>` Elements) | MEDIUM |
| **`ENG-03`** | `engagement-audit` | Onsite Engagement | Ambiguous Call-To-Action (CTA) Button Labels ("Click Here") | LOW |
| **`ENG-04`** | `engagement-audit` | Onsite Engagement | Missing Breadcrumb Navigation on Deep Subpages | LOW |
| **`ENG-05`** | `engagement-audit` | Onsite Engagement | No `FAQPage` or `Speakable` JSON-LD Schema for AI Answer Engines | MEDIUM |


---

## AI Readiness Scoring Formula

The orchestrator computes a standardized **0–100 AI Readiness Score** after deduplicating findings across all pages:

$$\text{Score} = \max\left(0, 100 - \sum \text{Deductions}\right)$$

| Severity | Deduction | Rationale |
| :--- | :--- | :--- |
| **CRITICAL** | **-25 pts** | Blocks automated crawler access entirely (unreachable site, server down). |
| **HIGH** | **-15 pts** | Prevents AI discovery or machine extraction (AI bot blocked in robots.txt, hydration lock, missing organization schema). |
| **MEDIUM** | **-7 pts** | Degrades extractability or entity authority (missing `/llms.txt`, no sitemap, outdated copyright, missing FAQ schema). |
| **LOW** | **-3 pts** | Sub-optimal semantic hygiene (missing alt text, heading hierarchy skip, missing canonical tag). |
