#!/usr/bin/env python3
"""Create a synthetic student paused at the first consented photo task."""

from __future__ import annotations

import argparse
import json
import os

import httpx

from live_cjm_gate import (
    api,
    auth_client,
    continue_state,
    expect,
    finish_diagnostic,
    fresh_phone,
)


def validate_test_pin(pin: str | None) -> str:
    if pin is None or not 4 <= len(pin) <= 12:
        raise SystemExit("KODI_TEST_PIN must contain 4 to 12 characters")
    return pin


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8414")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    pin = validate_test_pin(os.environ.get("KODI_TEST_PIN"))

    phone = fresh_phone(base_url, "709")
    with httpx.Client(base_url=base_url, timeout=60) as anonymous:
        registered = expect(
            anonymous.post(
                "/api/auth/phone/register",
                json={
                    "phone": phone,
                    "name": "Синтетический provider recovery",
                    "pin": pin,
                    "grade": 6,
                },
            ),
            200,
            "provider account register",
        )

    with auth_client(base_url, str(registered["access_token"])) as client:
        state = api(client, "GET", "/api/journey/current")
        state = api(
            client,
            "POST",
            "/api/journey/profile",
            body={
                "revision": state["revision"],
                "target": "nis-grade-7",
                "weekly_goal": 4,
                "session_minutes": 30,
                "target_window": "spring-2027",
                "prep_experience": "self",
                "weak_topics": ["PC05"],
                "strong_topics": ["EQ04"],
                "mock_math_band": "21-30",
                "language": "ru",
            },
        )
        state = continue_state(client, state, "open_diagnostic_intro")
        state = continue_state(client, state, "start_diagnostic")
        state = finish_diagnostic(
            client,
            state,
            wrong={321: "1200"},
            label="provider-recovery",
        )
        state = continue_state(client, state, "show_route")
        state = continue_state(client, state, "start_lesson")
        state = continue_state(client, state, "start_task")
        api(
            client,
            "POST",
            "/api/trainer/consent",
            body={"photo_consent": True},
        )
        state = api(client, "GET", "/api/journey/current")

    step = state["next_step"]
    assert step["type"] == "independent_task", step
    assert step["problem"]["content_idx"] == 1765, step
    assert step["photo_consent_required"] is False, step
    print(
        json.dumps(
            {
                "phone": phone,
                "stage": step["type"],
                "contentIdx": step["problem"]["content_idx"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
