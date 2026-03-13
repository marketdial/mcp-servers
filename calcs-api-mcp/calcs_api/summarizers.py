"""Response summarization and size management for Calcs API data.

Converts raw API responses (often 200k+ chars) into compact, LLM-friendly
summaries. This is the core layer that makes the MCP server usable —
since upstream API endpoints are fixed, all intelligence lives here.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("calcs-api.summarizers")

SAFE_TOKEN_LIMIT = 40_000  # Conservative limit to prevent context overflow


# ── Token estimation ───────────────────────────────────────────────────

def estimate_tokens(data: Any) -> int:
    """Estimate token count for a data structure (~4 chars per token)."""
    return len(json.dumps(data, ensure_ascii=False)) // 4


# ── Test results summarization ─────────────────────────────────────────

def summarize_test_results(raw_results: Any) -> dict:
    """Extract final lift/confidence from time-series arrays into a compact summary.

    The raw API response for OVERALL filter contains per-site time-series data
    with values in BASIS POINTS (divide by 100 for percentages). This function
    extracts just the final data point from each metric.

    Returns ~200-500 tokens instead of 225k+ characters.
    """
    if not raw_results:
        return {"status": "no_data", "message": "No results data returned"}

    # Handle both list and dict responses
    results_list = raw_results if isinstance(raw_results, list) else [raw_results]

    metrics = {}
    test_info = {}
    is_incomplete = False

    for result in results_list:
        if not isinstance(result, dict):
            continue

        # Extract test metadata from first result
        if not test_info:
            test_info = {
                "test_id": result.get("test_id"),
                "run_id": result.get("run_id"),
                "uuid": result.get("uuid"),
            }

        # Check completeness
        if result.get("is_incomplete"):
            is_incomplete = True

        # Extract metric name
        metric_name = result.get("metric_name") or result.get("out_metric_name", "unknown")

        # Extract final lift and confidence from time-series arrays
        out_lift = result.get("out_lift")
        out_confidence = result.get("out_confidence")
        out_numeric_lift = result.get("out_numeric_lift")

        if isinstance(out_lift, list) and len(out_lift) > 0:
            # Values are in basis points — convert to percentages
            final_lift_bp = out_lift[-1]
            final_lift_pct = final_lift_bp / 100.0 if isinstance(final_lift_bp, (int, float)) else None
        else:
            final_lift_pct = None

        if isinstance(out_confidence, list) and len(out_confidence) > 0:
            final_conf_bp = out_confidence[-1]
            final_conf_pct = final_conf_bp / 100.0 if isinstance(final_conf_bp, (int, float)) else None
        else:
            final_conf_pct = None

        # Numeric lift (absolute dollar/unit change)
        final_numeric_lift = None
        if isinstance(out_numeric_lift, list) and len(out_numeric_lift) > 0:
            final_numeric_lift = out_numeric_lift[-1]

        # Determine significance
        significant = final_conf_pct is not None and final_conf_pct >= 95.0

        metrics[metric_name] = {
            "lift_pct": round(final_lift_pct, 2) if final_lift_pct is not None else None,
            "confidence_pct": round(final_conf_pct, 2) if final_conf_pct is not None else None,
            "significant": significant,
            "numeric_lift": round(final_numeric_lift, 2) if final_numeric_lift is not None else None,
            "weeks_of_data": len(out_lift) if isinstance(out_lift, list) else 0,
        }

    # Generate verdict
    verdict = _generate_test_verdict(metrics, is_incomplete)

    return {
        **test_info,
        "is_incomplete": is_incomplete,
        "metrics": metrics,
        "verdict": verdict,
    }


def _generate_test_verdict(metrics: dict, is_incomplete: bool) -> str:
    """Generate a human-readable verdict from metric summaries."""
    if is_incomplete:
        return "Test is still running — results are partial and may change."

    if not metrics:
        return "No metrics available."

    significant_positive = []
    significant_negative = []
    insignificant = []

    for name, m in metrics.items():
        if m["significant"]:
            if m["lift_pct"] is not None and m["lift_pct"] > 0:
                significant_positive.append(f"{name} +{m['lift_pct']}%")
            elif m["lift_pct"] is not None:
                significant_negative.append(f"{name} {m['lift_pct']}%")
        else:
            insignificant.append(name)

    parts = []
    if significant_positive:
        parts.append(f"Significant positive lift: {', '.join(significant_positive)}")
    if significant_negative:
        parts.append(f"Significant negative lift: {', '.join(significant_negative)}")
    if insignificant:
        parts.append(f"Not significant: {', '.join(insignificant)}")

    if not significant_positive and not significant_negative:
        return "No statistically significant results (confidence < 95% on all metrics)."

    return ". ".join(parts) + "."


# ── Tests list summarization ───────────────────────────────────────────

COMPACT_TEST_FIELDS = [
    "id", "test_name", "calcs_status", "calcs_started", "calcs_ended",
    "date_created", "date_updated", "test_description",
]


def summarize_tests_list(
    tests: list[dict],
    sort_by: str = "calcs_ended",
    limit: int = 10,
    status_filter: str | None = None,
) -> dict:
    """Sort, filter, and compact a tests list for LLM consumption.

    Strips all nested objects and time-series data. Returns only the fields
    an LLM needs to identify and compare tests.
    """
    if not tests:
        return {"tests": [], "total": 0, "returned": 0}

    # Filter by status
    if status_filter:
        normalized = status_filter.upper()
        tests = [t for t in tests if (t.get("calcs_status") or "").upper() == normalized]

    # Sort (descending for dates, ascending for names)
    reverse = sort_by != "test_name"
    try:
        tests = sorted(
            tests,
            key=lambda t: t.get(sort_by) or "",
            reverse=reverse,
        )
    except (TypeError, KeyError):
        pass  # Keep original order if sort fails

    total = len(tests)
    tests = tests[:limit]

    # Compact: keep only essential fields
    compact = []
    for t in tests:
        compact.append({k: t.get(k) for k in COMPACT_TEST_FIELDS if k in t})

    return {"tests": compact, "total": total, "returned": len(compact)}


# ── Analysis results summarization ─────────────────────────────────────

def summarize_analysis_results(raw_results: dict, analysis_config: dict = None) -> dict:
    """Compact analysis results with is_incomplete prominently surfaced.

    Analysis results are already cleaner than test results (lift/confidence
    as plain floats, not basis point arrays), but we still need to surface
    completeness warnings and add verdicts.
    """
    if not raw_results:
        return {"status": "no_data", "message": "No results data returned"}

    metrics_data = raw_results.get("metrics", {})
    summary_data = raw_results.get("summary_data", {})

    # Check completeness
    actual_weeks = summary_data.get("actual_test_weeks", 0)
    requested_weeks = None
    if analysis_config:
        requested_weeks = analysis_config.get("measurementLength")

    is_incomplete = raw_results.get("is_incomplete", False)
    if requested_weeks and actual_weeks < requested_weeks:
        is_incomplete = True

    metrics = {}
    for name, m in metrics_data.items():
        if not isinstance(m, dict):
            continue
        lift = m.get("lift")
        confidence = m.get("confidence")
        significant = confidence is not None and confidence >= 95.0

        metrics[name] = {
            "lift_pct": round(lift, 2) if lift is not None else None,
            "confidence_pct": round(confidence, 2) if confidence is not None else None,
            "significant": significant,
        }

    # Generate verdict
    verdict = _generate_analysis_verdict(metrics, is_incomplete, actual_weeks, requested_weeks)

    result = {
        "is_incomplete": is_incomplete,
        "actual_weeks": actual_weeks,
        "metrics": metrics,
        "verdict": verdict,
    }
    if requested_weeks:
        result["requested_weeks"] = requested_weeks

    return result


def _generate_analysis_verdict(
    metrics: dict, is_incomplete: bool, actual_weeks: int, requested_weeks: int | None
) -> str:
    """Generate a verdict for analysis results."""
    if is_incomplete:
        week_info = f"{actual_weeks}/{requested_weeks}" if requested_weeks else str(actual_weeks)
        return (
            f"WARNING: Only {week_info} weeks of data available. "
            "Results are preliminary and should not be used for decisions."
        )
    return _generate_test_verdict(metrics, is_incomplete=False)


# ── Generic response size management ───────────────────────────────────

def smart_truncate_response(data: Any, keywords: list[str] | None = None) -> dict:
    """Manage response size with optional keyword filtering.

    Used as a safety net for tools that return raw API data.
    Prefer using specific summarizers (summarize_test_results, etc.) instead.
    """
    token_count = estimate_tokens(data)

    if token_count <= SAFE_TOKEN_LIMIT:
        return {
            "data": data,
            "truncated": False,
            "token_estimate": token_count,
            "total_records": len(data) if isinstance(data, list) else 1,
        }

    # Try keyword filtering
    if keywords:
        filtered = filter_json_by_keywords(data, keywords)
        filtered_tokens = estimate_tokens(filtered)
        if filtered_tokens <= SAFE_TOKEN_LIMIT:
            return {
                "data": filtered,
                "truncated": False,
                "filtered": True,
                "token_estimate": filtered_tokens,
                "original_token_estimate": token_count,
                "filter_keywords": keywords,
            }

    # Truncate lists item by item
    if isinstance(data, list):
        truncated = []
        current = 0
        for item in data:
            item_tokens = estimate_tokens(item)
            if current + item_tokens > SAFE_TOKEN_LIMIT:
                break
            truncated.append(item)
            current += item_tokens

        logger.warning(f"Truncated: {len(truncated)}/{len(data)} records")
        return {
            "data": truncated,
            "truncated": True,
            "token_estimate": current,
            "original_token_estimate": token_count,
            "total_records": len(data),
            "returned_records": len(truncated),
        }

    # Non-list oversized response
    logger.warning(f"Large non-list response ({token_count} tokens)")
    return {
        "data": {"summary": "Response too large — use a summary tool or filter_keywords"},
        "truncated": True,
        "token_estimate": token_count,
    }


def filter_json_by_keywords(data: Any, keywords: list[str]) -> dict:
    """Recursively extract fields matching keywords from JSON data."""
    if not keywords:
        return data

    def extract(obj: Any, path: str = "") -> dict:
        result = {}
        if isinstance(obj, dict):
            for key, value in obj.items():
                current = f"{path}.{key}" if path else key
                if any(kw.lower() in key.lower() or kw.lower() in current.lower() for kw in keywords):
                    result[current] = value
                elif isinstance(value, (dict, list)):
                    result.update(extract(value, current))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                result.update(extract(item, f"{path}[{i}]" if path else f"[{i}]"))
        return result

    if isinstance(data, list):
        filtered = [extract(item) for item in data]
        return {
            "filtered_results": [f for f in filtered if f],
            "total_records": len(data),
            "filtered_fields": keywords,
        }
    return {
        "filtered_results": extract(data),
        "filtered_fields": keywords,
    }
