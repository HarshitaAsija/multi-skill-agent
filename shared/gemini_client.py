"""
Google Gemini API Client for Agent Skill Marketplace.

Provides real LLM reasoning for:
  1. AI Answerability Evaluation (reading real website text to evaluate question answerability)
  2. Dynamic, Site-Tailored Proactive Recommendations (not generic templates)
  3. Executive AI Discoverability Synthesis & Query Simulation

Zero third-party dependencies: uses standard library urllib.request and json.
Gracefully falls back to deterministic analysis when no API key is present.
"""

import os
import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from shared.logging_utils import get_logger

logger = get_logger("gemini_client")


def _load_env_if_present(filepath: str = ".env") -> None:
    """Loads environment variables from .env file if it exists."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            logger.debug(f"Failed to load .env file: {e}")


# Automatically check for .env on module load
_load_env_if_present()


class GeminiClient:
    """
    Client for Google Gemini REST API.
    Interacts with models like gemini-2.5-flash and gemini-1.5-flash.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    FALLBACK_MODEL = "gemini-1.5-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 30.0
    ):
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        ).strip()
        self.model = model
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """Returns True if a valid Gemini API key is configured."""
        return bool(self.api_key and len(self.api_key) > 5)

    def _call_gemini_api(self, prompt: str, model_name: str) -> Optional[str]:
        """Performs raw POST request to Gemini REST API."""
        endpoint = f"{self.BASE_URL}/{model_name}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return None
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.warning(f"Gemini API HTTP {e.code} error on model {model_name}: {err_body[:200]}")
            return None
        except Exception as e:
            logger.warning(f"Gemini API request failed on model {model_name}: {e}")
            return None

    def generate_json(self, prompt: str) -> Optional[Any]:
        """
        Sends prompt to Gemini expecting a valid JSON response.
        Attempts primary model first, falls back to secondary model if needed.
        """
        if not self.is_available():
            return None

        # 1. Try primary model
        raw_text = self._call_gemini_api(prompt, self.model)
        if not raw_text and self.model != self.FALLBACK_MODEL:
            logger.info(f"Retrying with fallback Gemini model: {self.FALLBACK_MODEL}")
            raw_text = self._call_gemini_api(prompt, self.FALLBACK_MODEL)

        if not raw_text:
            return None

        # Clean potential markdown wrapping (e.g. ```json ... ```)
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode JSON from Gemini output: {e}\nRaw output: {cleaned[:300]}")
            return None

    def evaluate_website_answerability(
        self,
        brand: str,
        root_url: str,
        industry_label: str,
        questions: List[Dict[str, Any]],
        aggregated_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini to thoroughly evaluate how an AI assistant (ChatGPT, Perplexity, Gemini)
        answers high-intent user questions based strictly on real website content.
        """
        if not self.is_available():
            return None

        # Truncate content safely to fit well within context limits
        content_sample = aggregated_content[:15000]

        questions_list_str = "\n".join(
            [f"- ID: {q['id']} | Question: {q['question']}" for q in questions]
        )

        prompt = f"""You are an elite AI Search & Retrieval Auditor evaluating whether conversational AI assistants (Perplexity, SearchGPT, Gemini, ChatGPT) can accurately answer key customer questions about the business '{brand}' ({root_url}).

Target Industry: {industry_label}

EXTRACTED REAL WEBSITE CONTENT:
\"\"\"
{content_sample}
\"\"\"

QUESTIONS TO AUDIT:
{questions_list_str}

TASK:
Based strictly on the provided real website content:
1. For each question, decide its answerability:
   - "ANSWERABLE": The text contains explicit, concrete facts, prices, policies, or details.
   - "PARTIAL": The topic is mentioned vaguely, but critical specifics (hours, prices, terms) are missing.
   - "NOT_ANSWERABLE": The website content provides no relevant details.
2. Cite the exact evidence or quote found (or specifically explain what key detail is absent).
3. Formulate a realistic query an end-user would ask an AI assistant about this brand.
4. Assess the specific hallucination or customer drop-off risk for an AI assistant.
5. Create an accurate, non-templated Schema.org Question/Answer pair using real details where available, or specific factual text.

Return your response strictly as a JSON object with this exact structure:
{{
  "detected_industry_refined": "{industry_label}",
  "industry_summary": "A 1-2 sentence description of what this business actually offers.",
  "questions": [
    {{
      "id": "question_id_matching_input",
      "question": "question_text_matching_input",
      "status": "ANSWERABLE" or "PARTIAL" or "NOT_ANSWERABLE",
      "evidence_found": "Specific quote or explanation of missing details",
      "simulated_prompt": "Realistic user query to an AI assistant about this brand",
      "ai_risk": "Specific AI hallucination or business risk",
      "action_title": "Clear remediation action",
      "why": "Why this matters for AI discoverability",
      "impact": "HIGH" or "MEDIUM" or "LOW",
      "effort": "LOW" or "MEDIUM" or "HIGH",
      "faq_q": "Specific question for FAQ schema",
      "faq_a": "Specific answer text with real facts"
    }}
  ]
}}
"""
        return self.generate_json(prompt)

    def generate_site_tailored_recommendations(
        self,
        brand: str,
        root_url: str,
        industry_label: str,
        findings_summary: List[Dict[str, Any]],
        site_content_summary: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Uses Gemini to generate 4-5 proactive, non-generic architectural and content
        recommendations uniquely tailored to this specific website and industry.
        """
        if not self.is_available():
            return None

        findings_brief = "\n".join(
            [f"- [{f.get('severity')}] {f.get('id')}: {f.get('title')}" for f in findings_summary[:10]]
        )

        prompt = f"""You are an elite AI Discoverability & Search Architecture consultant for '{brand}' ({root_url}).
Industry: {industry_label}

TECHNICAL AUDIT FINDINGS:
{findings_brief if findings_brief else "No critical technical errors."}

SITE CONTENT CONTEXT:
\"\"\"
{site_content_summary[:6000]}
\"\"\"

TASK:
Generate 4-5 forward-looking, proactive, site-specific recommendations to maximize this website's discoverability, citation authority, and conversion in conversational AI systems (Perplexity, ChatGPT, Claude, Google AI Overviews).
Avoid generic fluff. Provide real, concrete architectural and domain-specific guidance (e.g. specific Schema.org types, RAG chunking layout, API endpoints, citation anchors, entity disambiguation).

Every recommendation MUST strictly use one of these categories:
- "ai_discoverability"
- "machine_readiness"
- "factual_freshness"
- "onsite_engagement"

Return strictly a JSON array of recommendation objects with this exact structure:
[
  {{
    "id": "REC-AI-01-...",
    "title": "Clear, concise recommendation title",
    "category": "one of the 4 allowed categories above",
    "rationale": "Why this specific recommendation is vital for {brand} in {industry_label} based on its content and findings.",
    "suggested_implementation": "Actionable, concrete engineering or editorial steps to implement this."
  }}
]
"""
        res = self.generate_json(prompt)
        if isinstance(res, list):
            return res
        elif isinstance(res, dict) and "recommendations" in res and isinstance(res["recommendations"], list):
            return res["recommendations"]
        return None

    def generate_executive_synthesis(
        self,
        brand: str,
        root_url: str,
        score: int,
        industry_label: str,
        total_findings: int,
        coverage_pct: int
    ) -> Optional[str]:
        """
        Generates a concise executive assessment summarizing the brand's AI readiness.
        """
        if not self.is_available():
            return None

        prompt = f"""Write a 2-3 paragraph executive summary of the AI Discoverability & Search Engine Readiness audit for {brand} ({root_url}).
Metrics:
- AI Readiness Score: {score}/100
- Industry: {industry_label}
- Technical Issues Found: {total_findings}
- Market Question Answerability Coverage: {coverage_pct}%

Explain clearly:
1. How current conversational AI engines perceive and retrieve this site today.
2. The primary vulnerability (e.g. hallucination risk, missing entity validation, or conversion leakage).
3. The strategic priority for the leadership team to dominate AI-driven discovery.

Keep tone professional, analytical, authoritative. Return plain text without JSON.
"""
        endpoint = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except Exception as e:
            logger.debug(f"Executive synthesis generation skipped: {e}")
        return None
