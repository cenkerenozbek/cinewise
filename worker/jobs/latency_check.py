"""p95 latency check for recommendation and search endpoints.

Simulates N concurrent users making repeated requests and reports
p50 / p95 / p99 response times.

Targets (from proposal):
  - POST /api/recommendations  <  3 000 ms  at p95
  - GET  /api/movies?q=<query> <  2 000 ms  at p95

Usage:
    python jobs/latency_check.py [--base-url http://localhost:8000]
                                 [--concurrency 10] [--rounds 20]
                                 [--output-path /artifacts/latency.json]
"""

import argparse
import asyncio
import json
import logging
import os
import statistics
import time
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# p95 SLA targets in milliseconds
SLA_RECOMMENDATIONS_MS = 3000
SLA_SEARCH_MS = 2000

_GENRE_SETS = [
    ["Action", "Thriller"],
    ["Comedy", "Romance"],
    ["Drama", "Crime"],
    ["Science Fiction", "Adventure"],
    ["Horror", "Mystery"],
    ["Animation", "Family"],
    ["Documentary"],
    ["Fantasy", "Action"],
    ["History", "Drama"],
    ["Music", "Comedy"],
]

_SEARCH_QUERIES = [
    "inception",
    "dark knight",
    "star wars",
    "avengers",
    "matrix",
    "parasite",
    "interstellar",
    "pulp fiction",
    "godfather",
    "titanic",
]

_MOODS = ["Happy", "Tense", "Relaxing", "Mind-bending", "Romantic"]


async def measure_recommendation(
    client: httpx.AsyncClient,
    base_url: str,
    worker_id: int,
) -> float:
    """Send one recommendation request, return elapsed ms."""
    genres = _GENRE_SETS[worker_id % len(_GENRE_SETS)]
    mood = _MOODS[worker_id % len(_MOODS)]
    payload = {"genres": genres, "mood": mood}
    start = time.perf_counter()
    resp = await client.post(f"{base_url}/api/recommendations", json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000
    resp.raise_for_status()
    return elapsed_ms


async def measure_search(
    client: httpx.AsyncClient,
    base_url: str,
    worker_id: int,
) -> float:
    """Send one search request, return elapsed ms."""
    query = _SEARCH_QUERIES[worker_id % len(_SEARCH_QUERIES)]
    start = time.perf_counter()
    resp = await client.get(f"{base_url}/api/movies", params={"q": query, "page": 1})
    elapsed_ms = (time.perf_counter() - start) * 1000
    resp.raise_for_status()
    return elapsed_ms


async def run_concurrent_round(
    base_url: str,
    concurrency: int,
    endpoint: str,
) -> list[float]:
    """Fire `concurrency` requests simultaneously, return list of elapsed_ms."""
    limits = httpx.Limits(max_connections=concurrency + 5, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
        if endpoint == "recommendations":
            tasks = [
                measure_recommendation(client, base_url, i)
                for i in range(concurrency)
            ]
        else:
            tasks = [
                measure_search(client, base_url, i)
                for i in range(concurrency)
            ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    timings: list[float] = []
    errors = 0
    for r in results:
        if isinstance(r, Exception):
            errors += 1
            logger.warning(f"Request error: {r}")
        else:
            timings.append(r)
    if errors:
        logger.warning(f"  {errors}/{concurrency} requests failed this round")
    return timings


def compute_stats(timings: list[float]) -> dict:
    if not timings:
        return {"n": 0, "min": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0, "mean": 0}
    s = sorted(timings)
    n = len(s)

    def pct(p: float) -> float:
        idx = max(0, min(n - 1, int(p / 100 * n)))
        return round(s[idx], 1)

    return {
        "n": n,
        "min": round(s[0], 1),
        "mean": round(statistics.mean(s), 1),
        "p50": pct(50),
        "p95": pct(95),
        "p99": pct(99),
        "max": round(s[-1], 1),
    }


async def benchmark(
    base_url: str,
    concurrency: int,
    rounds: int,
    endpoint: str,
    sla_ms: int,
) -> dict:
    logger.info(f"Benchmarking {endpoint} — {concurrency} concurrent users, {rounds} rounds ...")
    all_timings: list[float] = []

    for r in range(1, rounds + 1):
        timings = await run_concurrent_round(base_url, concurrency, endpoint)
        all_timings.extend(timings)
        if r % 5 == 0 or r == rounds:
            partial = compute_stats(all_timings)
            logger.info(
                f"  Round {r:>2}/{rounds}  n={partial['n']}  "
                f"p50={partial['p50']:.0f}ms  p95={partial['p95']:.0f}ms  p99={partial['p99']:.0f}ms"
            )

    stats = compute_stats(all_timings)
    passed = stats["p95"] <= sla_ms
    verdict = "PASS" if passed else "FAIL"
    logger.info(
        f"\n{'='*60}\n"
        f"  {endpoint.upper()}  {verdict}\n"
        f"  SLA target: p95 < {sla_ms} ms\n"
        f"  Observed:   p50={stats['p50']:.0f}ms  p95={stats['p95']:.0f}ms  p99={stats['p99']:.0f}ms\n"
        f"{'='*60}"
    )
    return {
        "endpoint": endpoint,
        "sla_ms": sla_ms,
        "stats": stats,
        "passed": passed,
        "concurrency": concurrency,
        "rounds": rounds,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args()

    # Warm-up: single request to each endpoint to load any caches
    logger.info("Warming up ...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            await client.post(
                f"{args.base_url}/api/recommendations",
                json={"genres": ["Action"], "mood": "Happy"},
            )
            await client.get(f"{args.base_url}/api/movies", params={"q": "test", "page": 1})
        except Exception as e:
            logger.error(f"Warm-up failed — is the backend running at {args.base_url}? ({e})")
            return

    rec_result = await benchmark(
        args.base_url, args.concurrency, args.rounds,
        "recommendations", SLA_RECOMMENDATIONS_MS,
    )
    search_result = await benchmark(
        args.base_url, args.concurrency, args.rounds,
        "search", SLA_SEARCH_MS,
    )

    overall_pass = rec_result["passed"] and search_result["passed"]
    output = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "base_url": args.base_url,
        "overall_pass": overall_pass,
        "results": [rec_result, search_result],
    }

    out_path = args.output_path or os.path.join(
        os.environ.get("ARTIFACTS_DIR", "/artifacts"), "latency.json"
    )
    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Results written to: {out_path}")

    overall_label = "ALL PASS" if overall_pass else "SOME FAIL"
    logger.info(f"\nFinal verdict: {overall_label}")


if __name__ == "__main__":
    asyncio.run(main())
