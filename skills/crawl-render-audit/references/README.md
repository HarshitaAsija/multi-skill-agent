# Crawl, Render & Extractability Audit Reference Guide

## 1. Scope & Objective
The `crawl-render-audit` skill evaluates how search indexers, RAG pipelines, and autonomous AI agents retrieve, render, and extract structured knowledge from a target domain.

## 2. Recognized AI Crawler User-Agents (RFC 9309)
The skill parses `robots.txt` per RFC 9309 specifications to detect disallow directives targeting major AI retrieval engines:

| User-Agent | Organization / Model Family | Primary Role |
| :--- | :--- | :--- |
| `GPTBot` | OpenAI (ChatGPT, SearchGPT) | Web crawler for knowledge indexing & training |
| `ChatGPT-User` | OpenAI (Custom GPTs & Browsing) | Real-time user query web browsing |
| `PerplexityBot` | Perplexity AI | Real-time retrieval for conversational answers |
| `ClaudeBot` | Anthropic (Claude 3.x, Sonnet, Opus) | Knowledge grounding crawler |
| `anthropic-ai` | Anthropic | Training & data ingestion agent |
| `Google-Extended` | Google (Gemini, Vertex AI) | Content ingestion control for Gemini |
| `Applebot-Extended` | Apple (Apple Intelligence) | Generative training & knowledge graph builder |
| `Bytespider` | ByteDance (Doubao, TikTok AI) | Search and LLM crawling agent |
| `cohere-ai` | Cohere | Enterprise RAG indexing |

## 3. Template Bucket Sampling Strategy
Rather than crawling sequentially down an arbitrary depth link tree, the crawler classifies discovered URLs into representative template buckets with strict per-bucket quotas:
- **Homepage** (max 1): Root URL landing page.
- **About / Company** (max 3): Team, mission, contact, press.
- **Product / Pricing** (max 4): Commercial features, plans, pricing tiers, software applications.
- **Documentation / API** (max 4): Guides, references, SDK specs, integration docs.
- **Blog / Editorial** (max 3): News, changelogs, tutorials.
- **Generic** (max 5): Catch-all for other domain pages.

## 4. Context-Gated Structured Data Standards
To eliminate false positives:
- `Organization` / `WebSite` JSON-LD is only expected on root/homepages (`depth <= 2`).
- `Product` / `Offer` JSON-LD is only expected on commercial pages (`/pricing`, `/product`, `/plans`).
- Missing structured data on blog posts or documentation is never flagged as missing product schema.

## 5. Client-Side Hydration Lock Detection
Non-headless machine crawlers (such as standard PerplexityBot passes) parse server-rendered HTML. If a page's visible raw text contains `< 35` words while possessing framework mounting containers (`#root`, `#app`, `#__next`), it is flagged for client-side hydration dependency.
