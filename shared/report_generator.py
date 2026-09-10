"""
Audit Report Formatter & Exporter.

Converts structured AuditResult dictionaries into clean, publication-ready
GitHub-flavored Markdown reports with visual scorecards, question gap tables,
prioritized growth roadmaps, and ready-to-paste schema code blocks.
"""

import json
from typing import Dict, Any, List


def _clean_table_cell(text: Any) -> str:
    """Sanitizes text for safe inclusion inside Markdown table cells."""
    if text is None:
        return ""
    s = str(text).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return s.replace("|", "\\|").strip()


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """
    Generates a publication-grade Markdown audit document from an AuditResult dictionary.
    """
    site = report.get("site", "Unknown")
    audited_at = report.get("audited_at", "")
    ai_score = report.get("ai_readiness_score", 100)
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    recs = report.get("proactive_recommendations", [])
    mi = report.get("market_intelligence")

    lines: List[str] = []

    # Title & Metadata
    lines.append(f"# AI Readiness & Market Intelligence Audit Report")
    lines.append(f"")
    lines.append(f"**Target Site:** `{site}`  ")
    lines.append(f"**Audited At:** `{audited_at}`  ")
    lines.append(f"**AI Readiness Score:** `{ai_score} / 100`  ")
    if mi:
        lines.append(f"**Detected Industry:** {mi.get('industry_label', 'General Business')}  ")
        lines.append(f"**Market Question Coverage:** `{mi.get('market_question_coverage_pct', 0)}%` ({mi.get('clear_count', 0)} Answerable, {mi.get('partial_count', 0)} Partial, {mi.get('missing_count', 0)} Missing)  ")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Executive Scorecard
    lines.append(f"## 1. Executive Scorecard")
    lines.append(f"")
    lines.append(f"| Metric | Result | Status |")
    lines.append(f"| :--- | :--- | :--- |")
    status_label = "Optimal" if ai_score >= 80 else ("Needs Improvement" if ai_score >= 50 else "Critical Attention")
    lines.append(f"| **AI Readiness Score** | **{ai_score} / 100** | {status_label} |")
    if mi:
        cov = mi.get("market_question_coverage_pct", 0)
        cov_label = "Strong Coverage" if cov >= 80 else ("Moderate Gaps" if cov >= 50 else "High Gaps")
        lines.append(f"| **Market Question Coverage** | **{cov}%** | {cov_label} |")
    lines.append(f"| **Total Technical Findings** | **{summary.get('total_findings', 0)}** | {summary.get('critical', 0)} Critical, {summary.get('high', 0)} High, {summary.get('medium', 0)} Med, {summary.get('low', 0)} Low |")
    lines.append(f"")

    exec_synth = report.get("executive_synthesis")
    if exec_synth:
        lines.append(f"### Executive AI Discoverability Synthesis (Google Gemini)")
        lines.append(f"")
        lines.append(exec_synth)
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")

    # Market Intelligence & Question Gap Analysis
    if mi:
        lines.append(f"## 2. AI Answerability & Question Gap Analysis")
        lines.append(f"")
        lines.append(f"Evaluates what high-intent questions conversational AI assistants (e.g. ChatGPT, Perplexity, Gemini, Siri) can answer about **{site}** based on currently published content.")
        lines.append(f"")
        lines.append(f"| Status | High-Intent Question | Simulated AI Query | AI Assistant Risk / Outcome |")
        lines.append(f"| :--- | :--- | :--- | :--- |")
        status_icons = {
            "ANSWERABLE": "Answerable",
            "PARTIAL": "Partial",
            "NOT_ANSWERABLE": "Missing Gap",
        }
        for q in mi.get("questions", []):
            st = status_icons.get(q.get("status"), q.get("status"))
            q_text = _clean_table_cell(q.get("question", ""))
            prompt = _clean_table_cell(q.get("simulated_prompt", ""))
            risk = _clean_table_cell(q.get("ai_risk", ""))
            lines.append(f"| **{st}** | {q_text} | *\"{prompt}\"* | {risk} |")
        lines.append(f"")

        # Smart Growth Roadmap
        roadmap = mi.get("roadmap", [])
        if roadmap:
            lines.append(f"### Smart Growth Roadmap (Prioritized Action Plan)")
            lines.append(f"")
            lines.append(f"| Priority | Action Item | Expected Impact | Dev Effort | Business Rationale |")
            lines.append(f"| :--- | :--- | :--- | :--- | :--- |")
            for item in roadmap:
                act_title = _clean_table_cell(item.get('action_title'))
                imp = _clean_table_cell(item.get('impact'))
                eff = _clean_table_cell(item.get('effort'))
                why_text = _clean_table_cell(item.get('why'))
                lines.append(f"| **Priority {item.get('priority')}** | {act_title} | `{imp}` | `{eff}` | {why_text} |")
            lines.append(f"")

            # Ready to Paste FAQ Schema Snippets
            lines.append(f"### Ready-to-Paste FAQ Schema Remediations")
            lines.append(f"")
            lines.append(f"Copy and paste the following Schema.org JSON-LD blocks into your website `<head>` to immediately close detected question gaps:")
            lines.append(f"")
            faq_entities = [item.get("suggested_faq_json_ld") for item in roadmap if item.get("suggested_faq_json_ld")]
            if faq_entities:
                composite_faq = {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": faq_entities,
                }
                lines.append(f"```html")
                lines.append(f'<script type="application/ld+json">')
                lines.append(json.dumps(composite_faq, indent=2))
                lines.append(f"</script>")
                lines.append(f"```")
                lines.append(f"")

        lines.append(f"---")
        lines.append(f"")

    # Technical Findings Section
    lines.append(f"## 3. Technical Audit Findings")
    lines.append(f"")
    if not findings:
        lines.append(f"No technical issues detected. Site demonstrates high machine extractability and AI readiness.")
        lines.append(f"")
    else:
        for idx, f in enumerate(findings, 1):
            sev = f.get("severity", "LOW").upper()
            fid = f.get("id", "")
            title = f.get("title", "")
            cat = f.get("category", "")
            rationale = f.get("rationale", "")
            ev = f.get("evidence", {})
            action = f.get("suggested_action", {})
            urls = f.get("affected_urls", [])

            lines.append(f"### {idx}. [{sev}] {title}")
            lines.append(f"")
            lines.append(f"- **Finding ID:** `{fid}`")
            lines.append(f"- **Category:** `{cat}`")
            lines.append(f"- **Severity:** `{sev}`")
            lines.append(f"- **Observation:** {ev.get('observation', 'N/A')}")
            lines.append(f"- **Why It Matters:** {rationale}")
            lines.append(f"- **Remediation:** {action.get('summary', 'N/A')}")
            remed_steps = action.get("remediation_steps", [])
            if remed_steps:
                lines.append(f"- **Action Steps:**")
                for s in remed_steps:
                    lines.append(f"  1. {s}")
            lines.append(f"- **Affected URLs ({len(urls)}):**")
            for u in urls[:5]:
                lines.append(f"  - `{u}`")
            if len(urls) > 5:
                lines.append(f"  - *...and {len(urls) - 5} more page(s)*")
            lines.append(f"")

    # Proactive Recommendations
    if recs:
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 4. Proactive Architecture Recommendations")
        lines.append(f"")
        for r in recs:
            lines.append(f"#### {r.get('title')}")
            lines.append(f"- **Rationale:** {r.get('rationale')}")
            lines.append(f"- **Implementation:** {r.get('suggested_implementation')}")
            lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Report automatically generated by Adobe Agent Skill Marketplace Auditor.*")
    lines.append(f"")

    return "\n".join(lines)
