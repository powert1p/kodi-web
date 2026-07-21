#!/usr/bin/env python3
"""Two-fixture LIVE vision smoke with known ground truth.

The fixtures are synthetic notebook pages owned by this repository. The report
never includes an access token. A non-zero exit means Gemini did not separate
the correct and intentionally incorrect step reliably enough for the release bar.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import httpx


ROOT = Path(__file__).resolve().parent
DEFAULT_MATCH = ROOT / "fixtures/step-1-match.png"
DEFAULT_MISMATCH = ROOT / "fixtures/step-1-mismatch.png"


def expect(response: httpx.Response, status: int, label: str) -> dict:
    if response.status_code != status:
        raise AssertionError(
            f"{label}: expected {status}, got {response.status_code}: {response.text[:500]}"
        )
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8399")
    parser.add_argument("--match", type=Path, default=DEFAULT_MATCH)
    parser.add_argument("--mismatch", type=Path, default=DEFAULT_MISMATCH)
    parser.add_argument("--problem-id", type=int, default=3)
    parser.add_argument("--decomp-idx", type=int, default=2)
    parser.add_argument("--step-n", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--between-fixtures", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=30.0)
    args = parser.parse_args()

    phone = f"+77054{str(int(time.time() * 1000))[-7:]}"
    pin = "7319"
    base_url = args.base_url.rstrip("/")

    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        register = expect(
            client.post(
                "/api/auth/phone/register",
                json={
                    "phone": phone,
                    "name": "Синтетический Vision Eval",
                    "pin": pin,
                    "photo_consent": False,
                    "grade": 7,
                },
            ),
            200,
            "register",
        )
        headers = {"Authorization": f"Bearer {register['access_token']}"}
        expect(
            client.post(
                "/api/trainer/consent",
                headers=headers,
                json={"photo_consent": True},
            ),
            200,
            "technical canary consent",
        )

        verdicts: list[dict[str, object]] = []
        for index, (expected, fixture) in enumerate(
            (("match", args.match), ("mismatch", args.mismatch))
        ):
            if index:
                time.sleep(args.between_fixtures)

            attempts = 0
            while True:
                attempts += 1
                raw_response = client.post(
                    "/api/trainer/step-submit",
                    headers=headers,
                    data={
                        "problem_id": str(args.problem_id),
                        "decomp_idx": str(args.decomp_idx),
                        "step_n": str(args.step_n),
                    },
                    files={"photo": (fixture.name, fixture.read_bytes(), "image/png")},
                )
                if raw_response.status_code == 200:
                    response = raw_response.json()
                    break
                if raw_response.status_code != 503 or attempts >= args.retries:
                    response = expect(raw_response, 200, f"live Gemini {expected}")
                    break
                time.sleep(args.retry_delay)
            grounded_hint = (
                expected != "mismatch"
                or (
                    response["verdict"] == "mismatch"
                    and isinstance(response["hint"], str)
                    and response["hint"].startswith("Проверь этот шаг ещё раз:")
                )
            )
            verdicts.append(
                {
                    "fixture": str(fixture),
                    "expected": expected,
                    "actual": response["verdict"],
                    "confidence": response["confidence"],
                    "hint": response["hint"],
                    "attempts": attempts,
                    "correct": response["verdict"] == expected,
                    "grounded_hint": grounded_hint,
                }
            )

    passed = all(
        bool(item["correct"]) and bool(item["grounded_hint"])
        for item in verdicts
    )
    report = {
        "base_url": base_url,
        "synthetic_account": phone,
        "problem_id": args.problem_id,
        "decomp_idx": args.decomp_idx,
        "step_n": args.step_n,
        "expected_value": "91",
        "results": verdicts,
        "verdict": "PASS" if passed else "FAIL",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
