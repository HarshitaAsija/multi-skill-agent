# Freshness & Corroboration Audit Reference Guide

## 1. Scope & Objective
The `freshness-corroboration` skill audits temporal signals, content decay indicators, and cross-page entity claims to evaluate brand trustworthiness for AI search and conversational agents.

## 2. Temporal Decay & Copyright Anchors (`FRESH-01`)
AI search models (Perplexity, ChatGPT Search, Google Gemini) treat temporal markers as proxy indicators for site maintenance and authority:
- **Current Year**: Full freshness credit.
- **Previous Calendar Year**: Acceptable for static corporate content (no penalty).
- **2+ Years Outdated**: Flags `FRESH-01`. Suggests unmaintained infrastructure and triggers authority decay in retrieval algorithms.

## 3. Cross-Page Entity Consistency (`FRESH-02`)
When autonomous agents construct entity graphs, conflicting declarations across pages create entity disambiguation failure:
- Multiple differing `Organization` name attributes in Schema.org JSON-LD scripts across pages.
- Contradictory primary branding or contact identity points.
- Standardizing the canonical entity name across all templates ensures consistent representation across LLM knowledge bases.

## 4. Editorial & Article Temporal Anchors (`FRESH-03`)
- Technical guides and product documentation that display timestamps older than 2 years without `dateModified` updates are flagged as potentially obsolete.
- Search engines and RAG retrieval pipelines heavily favor recently modified content when answering user inquiries about features or APIs.
