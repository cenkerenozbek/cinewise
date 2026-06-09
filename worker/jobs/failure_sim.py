"""Failure simulation and graceful degradation tests.

Verifies the system handles failure modes correctly and falls back safely.

Scenarios tested:
  1. Normal operation — system returns 200 + recommendations
  2. Malformed request — missing required field → 422, not 500
  3. Unsupported mood — invalid enum value → 422 with message
  4. Health endpoint — returns 200 under normal conditions
  5. CF artifact missing — backend falls back to content-only (no crash)
  6. Main NLP artifact missing — backend returns 503, not 500

Scenarios 5 and 6 work by:
  - Renaming the artifact inside the Docker worker volume
  - Restarting the backend container to force re-load
  - Verifying the API response code
  - Restoring the artifact and restarting

Usage:
    python jobs/failure_sim.py [--base-url http://localhost:8000]
                               [--output-path /artifacts/failure_sim.json]
                               [--skip-destructive]   # skip scenarios 5 & 6
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BACKEND_CONTAINER = "ai-powered-mrs-backend-1"
ARTIFACTS_DIR = "/artifacts"

_VALID_PAYLOAD = {"genres": ["Action", "Thriller"], "mood": "Tense"}


def _docker(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker"] + cmd, capture_output=True, text=True, check=check)


def _restart_backend(wait: float = 6.0) -> None:
    logger.info(f"Restarting {BACKEND_CONTAINER} ...")
    _docker(["restart", BACKEND_CONTAINER])
    time.sleep(wait)


def _rename_artifact(src: str, dst: str) -> bool:
    result = _docker(
        ["exec", BACKEND_CONTAINER, "mv", f"{ARTIFACTS_DIR}/{src}", f"{ARTIFACTS_DIR}/{dst}"],
        check=False,
    )
    return result.returncode == 0


def _artifact_exists(name: str) -> bool:
    result = _docker(
        ["exec", BACKEND_CONTAINER, "test", "-f", f"{ARTIFACTS_DIR}/{name}"],
        check=False,
    )
    return result.returncode == 0


async def _post_recommendations(client: httpx.AsyncClient, base_url: str, payload: dict) -> tuple[int, dict | str]:
    try:
        resp = await client.post(f"{base_url}/api/recommendations", json=payload, timeout=15.0)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return resp.status_code, body
    except Exception as e:
        return 0, str(e)


async def _get_health(client: httpx.AsyncClient, base_url: str) -> tuple[int, dict | str]:
    try:
        resp = await client.get(f"{base_url}/api/health", timeout=10.0)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return resp.status_code, body
    except Exception as e:
        return 0, str(e)


def _result(name: str, passed: bool, expected: str, actual: str, detail: str = "") -> dict:
    label = "PASS" if passed else "FAIL"
    logger.info(f"  [{label}] {name}")
    if not passed or detail:
        logger.info(f"         expected: {expected}")
        logger.info(f"         actual  : {actual}")
        if detail:
            logger.info(f"         detail  : {detail}")
    return {
        "scenario": name,
        "passed": passed,
        "expected": expected,
        "actual": actual,
        "detail": detail,
    }


async def run_scenarios(base_url: str, skip_destructive: bool) -> list[dict]:
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=20.0) as client:

        # ------------------------------------------------------------------ #
        # 1. Normal operation
        # ------------------------------------------------------------------ #
        logger.info("\n=== Scenario 1: Normal operation ===")
        status, body = await _post_recommendations(client, base_url, _VALID_PAYLOAD)
        recs = body.get("recommendations", []) if isinstance(body, dict) else []
        passed = status == 200 and len(recs) > 0
        results.append(_result(
            "Normal operation",
            passed,
            "HTTP 200 with ≥1 recommendation",
            f"HTTP {status}, {len(recs)} recommendations",
            f"First rec: {recs[0].get('title') if recs else 'N/A'}",
        ))

        # ------------------------------------------------------------------ #
        # 2. Malformed request — missing required field
        # ------------------------------------------------------------------ #
        logger.info("\n=== Scenario 2: Missing required field ===")
        status, body = await _post_recommendations(client, base_url, {"mood": "Tense"})
        passed = status == 422
        detail = body.get("detail", str(body)) if isinstance(body, dict) else str(body)
        results.append(_result(
            "Missing required field (genres)",
            passed,
            "HTTP 422 Unprocessable Entity",
            f"HTTP {status}",
            str(detail)[:120],
        ))

        # ------------------------------------------------------------------ #
        # 3. Invalid mood value
        # ------------------------------------------------------------------ #
        logger.info("\n=== Scenario 3: Invalid mood enum ===")
        status, body = await _post_recommendations(client, base_url, {"genres": ["Action"], "mood": "INVALID_MOOD"})
        passed = status == 422
        detail = body.get("detail", str(body)) if isinstance(body, dict) else str(body)
        results.append(_result(
            "Invalid mood value",
            passed,
            "HTTP 422 with validation error",
            f"HTTP {status}",
            str(detail)[:120],
        ))

        # ------------------------------------------------------------------ #
        # 4. Health endpoint
        # ------------------------------------------------------------------ #
        logger.info("\n=== Scenario 4: Health endpoint ===")
        status, body = await _get_health(client, base_url)
        passed = status == 200
        results.append(_result(
            "Health endpoint",
            passed,
            "HTTP 200",
            f"HTTP {status}",
            str(body)[:120],
        ))

        # ------------------------------------------------------------------ #
        # 5. CF artifact missing → content-only fallback (no crash)
        # ------------------------------------------------------------------ #
        logger.info("\n=== Scenario 5: CF artifact missing ===")
        if skip_destructive:
            logger.info("  SKIPPED (--skip-destructive)")
            results.append(_result(
                "CF artifact missing — content-only fallback",
                True, "SKIPPED", "SKIPPED",
                "Pass skipped by flag",
            ))
        elif not _artifact_exists("cf_index.joblib"):
            logger.info("  cf_index.joblib not found — test not applicable")
            results.append(_result(
                "CF artifact missing — content-only fallback",
                True, "N/A", "N/A",
                "CF artifact was already absent; content-only is the normal mode",
            ))
        else:
            # Rename CF artifact, restart, test, restore
            renamed = _rename_artifact("cf_index.joblib", "cf_index.joblib.bak")
            if not renamed:
                results.append(_result(
                    "CF artifact missing — content-only fallback",
                    False, "Rename succeeded", "Docker rename failed",
                ))
            else:
                _restart_backend(wait=8.0)
                status, body = await _post_recommendations(client, base_url, _VALID_PAYLOAD)
                recs = body.get("recommendations", []) if isinstance(body, dict) else []
                # Expect: still works (content-only), not a crash
                passed = status == 200 and len(recs) > 0
                results.append(_result(
                    "CF artifact missing — content-only fallback",
                    passed,
                    "HTTP 200 with recommendations (content-only mode)",
                    f"HTTP {status}, {len(recs)} recommendations",
                ))
                # Restore
                _rename_artifact("cf_index.joblib.bak", "cf_index.joblib")
                _restart_backend(wait=8.0)

        # ------------------------------------------------------------------ #
        # 6. Main NLP artifact missing → 503 (not 500)
        # ------------------------------------------------------------------ #
        logger.info("\n=== Scenario 6: NLP artifact missing → 503 ===")
        if skip_destructive:
            logger.info("  SKIPPED (--skip-destructive)")
            results.append(_result(
                "NLP artifact missing → 503",
                True, "SKIPPED", "SKIPPED",
                "Pass skipped by flag",
            ))
        elif not _artifact_exists("similarity_index.joblib"):
            results.append(_result(
                "NLP artifact missing → 503",
                False, "Artifact present before rename", "similarity_index.joblib not found",
                "Cannot run test — artifact missing before scenario starts",
            ))
        else:
            renamed = _rename_artifact("similarity_index.joblib", "similarity_index.joblib.bak")
            if not renamed:
                results.append(_result(
                    "NLP artifact missing → 503",
                    False, "Rename succeeded", "Docker rename failed",
                ))
            else:
                _restart_backend(wait=8.0)
                status, body = await _post_recommendations(client, base_url, _VALID_PAYLOAD)
                # Expect 503 Service Unavailable (graceful), NOT 500
                passed = status == 503
                detail = body.get("detail", str(body)) if isinstance(body, dict) else str(body)
                results.append(_result(
                    "NLP artifact missing → 503",
                    passed,
                    "HTTP 503 with message (not 500)",
                    f"HTTP {status}",
                    str(detail)[:120],
                ))
                # Always restore regardless of test outcome
                _rename_artifact("similarity_index.joblib.bak", "similarity_index.joblib")
                _restart_backend(wait=8.0)
                # Verify system recovered
                status2, body2 = await _post_recommendations(client, base_url, _VALID_PAYLOAD)
                recs2 = body2.get("recommendations", []) if isinstance(body2, dict) else []
                recovery_ok = status2 == 200 and len(recs2) > 0
                results.append(_result(
                    "System recovery after NLP artifact restore",
                    recovery_ok,
                    "HTTP 200 after artifact restore",
                    f"HTTP {status2}, {len(recs2)} recommendations",
                ))

    return results


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--skip-destructive", action="store_true",
                        help="Skip scenarios that restart the backend container")
    args = parser.parse_args()

    logger.info(f"Failure simulation against: {args.base_url}")
    if args.skip_destructive:
        logger.info("Destructive scenarios will be SKIPPED")

    results = await run_scenarios(args.base_url, args.skip_destructive)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    overall = passed == total

    logger.info(f"\n{'='*60}")
    logger.info(f"FAILURE SIMULATION: {passed}/{total} scenarios passed")
    logger.info(f"Overall: {'ALL PASS' if overall else 'SOME FAIL'}")
    logger.info(f"{'='*60}")

    output = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "base_url": args.base_url,
        "passed": passed,
        "total": total,
        "overall_pass": overall,
        "results": results,
    }

    out_path = args.output_path or os.path.join(
        os.environ.get("ARTIFACTS_DIR", "/artifacts"), "failure_sim.json"
    )
    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Results written to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
