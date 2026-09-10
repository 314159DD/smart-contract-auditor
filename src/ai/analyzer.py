"""
AI-powered vulnerability analysis via OpenRouter (supports Claude, GPT, etc.).

Three tiers:
  quick    — static detectors only, no API call, <5 s
  standard — static + single-pass AI analysis, ~30 s
  deep     — static + three-pass AI analysis, ~2 min
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import openai

logger = logging.getLogger(__name__)

from src.ai.models import AIAnalysis, AIFinding
from src.ai.prompts import (
    SYSTEM_PROMPT,
    standard_scan_prompt,
    deep_audit_pass1_prompt,
    deep_audit_pass2_prompt,
    deep_audit_pass3_prompt,
)
from src.parser.models import Contract
from src.detectors.base import Vulnerability

# Default model via OpenRouter
_MODEL = "anthropic/claude-sonnet-4-6"
# Cost per million tokens (approximate — OpenRouter pricing)
_INPUT_COST_PER_M = 3.0   # $3 / M input tokens
_OUTPUT_COST_PER_M = 15.0  # $15 / M output tokens


# Cache settings
_CACHE_DIR = Path("data/ai_cache")
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

# Retry settings
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2  # seconds


class AIAnalyzer:
    """Orchestrates AI API calls via OpenRouter for smart contract security analysis."""

    def __init__(self, api_key: Optional[str] = None, model: str = _MODEL):
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY", ""),
        )
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        contract: Contract,
        static_findings: list,
        scan_type: str = "standard",
    ) -> AIAnalysis:
        """
        Run AI analysis at the requested tier.

        Args:
            contract: Parsed Contract object.
            static_findings: List of Vulnerability objects from static detectors.
            scan_type: "quick" | "standard" | "deep"

        Returns:
            AIAnalysis with findings, notes, and metadata.
        """
        if scan_type == "quick":
            # Quick scan = static only; no AI call
            return AIAnalysis(
                scan_type="quick",
                model_used="none (static-only)",
            )

        # Check cache
        cache_key = self._cache_key(contract.source, scan_type)
        cached = self._read_cache(cache_key)
        if cached is not None:
            logger.info("AI cache hit for %s scan (key=%s)", scan_type, cache_key[:12])
            self._cross_reference_findings(cached, static_findings)
            return cached

        start = time.monotonic()
        try:
            if scan_type == "standard":
                result = self._standard_pass(contract, static_findings)
            else:
                result = self._deep_passes(contract, static_findings)
        except Exception as exc:
            return AIAnalysis(
                scan_type=scan_type,
                model_used=self.model,
                analysis_time_seconds=time.monotonic() - start,
                error=str(exc),
            )

        result.scan_type = scan_type
        result.model_used = self.model
        result.analysis_time_seconds = time.monotonic() - start
        self._cross_reference_findings(result, static_findings)

        # Write to cache
        self._write_cache(cache_key, result)

        return result

    # ------------------------------------------------------------------
    # Internal passes
    # ------------------------------------------------------------------

    def _standard_pass(self, contract: Contract, static_findings: list) -> AIAnalysis:
        prompt = standard_scan_prompt(contract.source, contract.name, static_findings)
        response = self._call_ai(prompt)
        return self._parse_response(response)

    def _deep_passes(self, contract: Contract, static_findings: list) -> AIAnalysis:
        # Pass 1: broad sweep
        p1_prompt = deep_audit_pass1_prompt(contract.source, contract.name, static_findings)
        p1_response = self._call_ai(p1_prompt)
        p1_analysis = self._parse_response(p1_response)

        # Pass 2: cross-reference + PoC
        p2_prompt = deep_audit_pass2_prompt(contract.source, contract.name, p1_analysis.findings)
        p2_response = self._call_ai(p2_prompt)
        p2_analysis = self._parse_response(p2_response)

        # Pass 3: fix generation
        p3_prompt = deep_audit_pass3_prompt(contract.source, contract.name, p2_analysis.findings)
        p3_response = self._call_ai(p3_prompt)
        p3_analysis = self._parse_response(p3_response)

        # Accumulate token counts
        total_tokens = (
            p1_analysis.tokens_used
            + p2_analysis.tokens_used
            + p3_analysis.tokens_used
        )
        total_cost = p1_analysis.cost_usd + p2_analysis.cost_usd + p3_analysis.cost_usd

        p3_analysis.tokens_used = total_tokens
        p3_analysis.cost_usd = total_cost
        p3_analysis.business_logic_notes = p3_analysis.business_logic_notes or p1_analysis.business_logic_notes
        p3_analysis.centralization_risks = p3_analysis.centralization_risks or p1_analysis.centralization_risks
        p3_analysis.gas_optimizations = p3_analysis.gas_optimizations or p1_analysis.gas_optimizations
        return p3_analysis

    # ------------------------------------------------------------------
    # Claude API helper
    # ------------------------------------------------------------------

    def _call_ai(self, user_prompt: str, timeout_seconds: int = 120):
        """Call OpenRouter API with retry on rate limit and transient errors.

        Args:
            user_prompt: The prompt to send.
            timeout_seconds: Maximum wall-clock time per API call (default 120s).
        """
        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=timeout_seconds,
                    extra_headers={
                        "HTTP-Referer": "https://contractaudit.app",
                        "X-Title": "ContractAudit AI",
                    },
                )
            except openai.RateLimitError as exc:
                last_exc = exc
                wait = _RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning("Rate limited (attempt %d/%d), retrying in %ds", attempt + 1, _MAX_RETRIES, wait)
                time.sleep(wait)
            except openai.APIStatusError as exc:
                if exc.status_code >= 500:
                    last_exc = exc
                    wait = _RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning("API error %d (attempt %d/%d), retrying in %ds", exc.status_code, attempt + 1, _MAX_RETRIES, wait)
                    time.sleep(wait)
                else:
                    raise
            except openai.APITimeoutError as exc:
                logger.error("AI API call timed out after %ds (attempt %d/%d)", timeout_seconds, attempt + 1, _MAX_RETRIES)
                last_exc = exc
                break
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, response) -> AIAnalysis:
        raw_text = response.choices[0].message.content if response.choices else ""
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        cost = (
            input_tokens / 1_000_000 * _INPUT_COST_PER_M
            + output_tokens / 1_000_000 * _OUTPUT_COST_PER_M
        )

        analysis = AIAnalysis(
            scan_type="",
            tokens_used=input_tokens + output_tokens,
            cost_usd=cost,
        )

        # Strip potential markdown code fences
        json_text = raw_text.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("```", 2)[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
            json_text = json_text.rsplit("```", 1)[0]

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON object from surrounding text
            import re
            m = re.search(r"\{.*\}", json_text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    analysis.error = f"Could not parse AI response as JSON: {raw_text[:200]}"
                    return analysis
            else:
                analysis.error = f"No JSON object in AI response: {raw_text[:200]}"
                return analysis

        for raw_finding in data.get("findings", []):
            analysis.findings.append(AIFinding(
                severity=raw_finding.get("severity", "MEDIUM").upper(),
                title=raw_finding.get("title", "Untitled Finding"),
                description=raw_finding.get("description", ""),
                attack_scenario=raw_finding.get("attack_scenario", ""),
                affected_code=raw_finding.get("affected_code", ""),
                fix_before=raw_finding.get("fix_before", ""),
                fix_after=raw_finding.get("fix_after", ""),
                fix_explanation=raw_finding.get("fix_explanation", ""),
                real_world_examples=raw_finding.get("real_world_examples", []),
                confidence=raw_finding.get("confidence", "medium"),
            ))

        analysis.business_logic_notes = data.get("business_logic_notes", "")
        analysis.centralization_risks = data.get("centralization_risks", [])
        analysis.gas_optimizations = data.get("gas_optimizations", [])
        return analysis

    # ------------------------------------------------------------------
    # Confidence cross-referencing
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(source: str, scan_type: str) -> str:
        """Deterministic cache key from contract source + scan type."""
        return hashlib.sha256(f"{scan_type}:{source}".encode()).hexdigest()

    @staticmethod
    def _read_cache(key: str) -> Optional[AIAnalysis]:
        """Read cached AIAnalysis if it exists and hasn't expired."""
        path = _CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        try:
            age = time.time() - path.stat().st_mtime
            if age > _CACHE_TTL_SECONDS:
                path.unlink(missing_ok=True)
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            analysis = AIAnalysis(scan_type=data.get("scan_type", ""))
            analysis.model_used = data.get("model_used", "")
            analysis.tokens_used = data.get("tokens_used", 0)
            analysis.cost_usd = data.get("cost_usd", 0.0)
            analysis.analysis_time_seconds = data.get("analysis_time_seconds", 0.0)
            analysis.business_logic_notes = data.get("business_logic_notes", "")
            analysis.centralization_risks = data.get("centralization_risks", [])
            analysis.gas_optimizations = data.get("gas_optimizations", [])
            for fd in data.get("findings", []):
                analysis.findings.append(AIFinding(
                    severity=fd.get("severity", "MEDIUM"),
                    title=fd.get("title", ""),
                    description=fd.get("description", ""),
                    attack_scenario=fd.get("attack_scenario", ""),
                    affected_code=fd.get("affected_code", ""),
                    fix_before=fd.get("fix_before", ""),
                    fix_after=fd.get("fix_after", ""),
                    fix_explanation=fd.get("fix_explanation", ""),
                    real_world_examples=fd.get("real_world_examples", []),
                    confidence=fd.get("confidence", "medium"),
                ))
            return analysis
        except Exception:
            return None

    @staticmethod
    def _write_cache(key: str, analysis: AIAnalysis) -> None:
        """Persist AIAnalysis to disk cache."""
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "scan_type": analysis.scan_type,
                "model_used": analysis.model_used,
                "tokens_used": analysis.tokens_used,
                "cost_usd": analysis.cost_usd,
                "analysis_time_seconds": analysis.analysis_time_seconds,
                "business_logic_notes": analysis.business_logic_notes,
                "centralization_risks": analysis.centralization_risks,
                "gas_optimizations": analysis.gas_optimizations,
                "findings": [
                    {
                        "severity": f.severity,
                        "title": f.title,
                        "description": f.description,
                        "attack_scenario": f.attack_scenario,
                        "affected_code": f.affected_code,
                        "fix_before": f.fix_before,
                        "fix_after": f.fix_after,
                        "fix_explanation": f.fix_explanation,
                        "real_world_examples": f.real_world_examples,
                        "confidence": f.confidence,
                    }
                    for f in analysis.findings
                ],
            }
            path = _CACHE_DIR / f"{key}.json"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to write AI cache: %s", exc)

    # ------------------------------------------------------------------
    # Confidence cross-referencing
    # ------------------------------------------------------------------

    def _cross_reference_findings(
        self,
        ai_analysis: AIAnalysis,
        static_findings: list,
    ) -> None:
        """Boost confidence when AI and static detectors agree on the same issue."""
        static_titles_lower = {v.title.lower() for v in static_findings}
        static_detectors = {v.detector for v in static_findings}

        for finding in ai_analysis.findings:
            title_lower = finding.title.lower()
            # Check for keyword overlap
            overlaps = [st for st in static_titles_lower if
                        any(word in st for word in title_lower.split() if len(word) > 4)]
            if overlaps:
                finding.confirmed_by_static = True
                finding.detector_names = list(overlaps)
                if finding.confidence == "low":
                    finding.confidence = "medium"
                elif finding.confidence == "medium":
                    finding.confidence = "high"
