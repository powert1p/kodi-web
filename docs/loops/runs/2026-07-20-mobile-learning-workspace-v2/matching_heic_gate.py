#!/usr/bin/env python3
"""Prove that the real HEIC is evaluated against its matching task context."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


RUN_DIR = Path(__file__).resolve().parent
LEGACY_GATE_DIR = RUN_DIR.parent / "2026-07-20-answer-or-photo-mobile-live-review"
sys.path.insert(0, str(LEGACY_GATE_DIR))

import public_photo_cjm_gate as photo_gate  # noqa: E402


MATCHING_CONTENT_IDX = 1659
MATCHING_PROBLEM_ID = 1660


def token_subject(token: str) -> int:
    encoded = token.split(".")[1]
    padded = encoded + "=" * (-len(encoded) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return int(payload["sub"])


def set_matching_task(container: str, student_id: int) -> str:
    safe_student_id = int(student_id)
    sql = f"""
UPDATE student_journeys
SET stage = 'independent_task',
    revision = revision + 1,
    current_topic_id = 'FR05',
    current_problem_id = {MATCHING_PROBLEM_ID},
    current_decomp_idx = {MATCHING_CONTENT_IDX},
    activity = '{{"mode":"independent","guided_step":1,"support_used":false}}'::jsonb,
    feedback = '{{}}'::jsonb,
    completed_at = NULL,
    updated_at = NOW()
WHERE student_id = {safe_student_id};
"""
    completed = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            "kodi",
            "-d",
            "kodi",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "UPDATE 1" in completed.stdout, completed.stdout
    return completed.stdout.strip()


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "status": "RUNNING",
        "base_url": args.base_url.rstrip("/"),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "console_errors": [],
        "page_errors": [],
        "request_failures": [],
        "http_errors": [],
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 375, "height": 844},
                is_mobile=True,
                has_touch=True,
                reduced_motion="reduce",
                service_workers="block",
            )
            page = context.new_page()
            page.set_default_timeout(30_000)
            page.on(
                "console",
                lambda message: result["console_errors"].append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on(
                "requestfailed",
                lambda request: result["request_failures"].append(
                    f"{request.method} {request.url}: {request.failure}"
                ),
            )
            page.on(
                "response",
                lambda response: result["http_errors"].append(
                    f"{response.status} {response.url}"
                )
                if response.status >= 400
                else None,
            )

            provisioning = photo_gate.register_and_reach_pc06_task(
                page, result["base_url"]
            )
            token = page.evaluate("localStorage.getItem('kodi.jwt')")
            assert isinstance(token, str) and token, "synthetic session token is missing"
            student_id = token_subject(token)
            result["student_id"] = student_id
            result["database_update"] = set_matching_task(
                args.postgres_container, student_id
            )
            if args.token_file:
                token_file = args.token_file.resolve()
                token_file.write_text(token, encoding="utf-8")
                os.chmod(token_file, 0o600)
                result["token_file"] = str(token_file)
            if args.credentials_file:
                credentials_file = args.credentials_file.resolve()
                credentials_file.write_text(
                    json.dumps(provisioning["credentials"], ensure_ascii=False),
                    encoding="utf-8",
                )
                os.chmod(credentials_file, 0o600)
                result["credentials_file"] = str(credentials_file)

            page.reload(wait_until="domcontentloaded")
            photo_gate.wait_workspace(page)
            matching_state = photo_gate.current_state(page)
            marker = photo_gate.task_marker(matching_state)
            assert marker["content_idx"] == MATCHING_CONTENT_IDX, marker
            assert "3/7" in str(marker["statement"]), marker
            assert "4/9" in str(marker["statement"]), marker
            result["matching_task"] = marker
            result["consent"] = photo_gate.grant_photo_consent(page)
            result["geometry"] = photo_gate.geometry(
                page,
                375,
                844,
                "matching-task-375x844",
                output_dir,
                mode_switch_name="Ввести ответ",
            )

            upload = photo_gate.upload_photo(
                page, args.heic.resolve(), output_dir, "matching-heic"
            )
            result["heic"] = upload
            state = photo_gate.current_state(page)
            step = state.get("next_step") or {}
            result["ai_feedback"] = {
                key: step.get(key)
                for key in (
                    "type",
                    "verdict",
                    "reason",
                    "message",
                    "feedback",
                    "next_action",
                )
                if step.get(key) is not None
            }
            assert upload["stage"] in {"photo_feedback", "transfer_feedback"}, upload
            assert upload.get("reason") not in {"wrong_photo", "unclear_photo"}, upload
            assert upload.get("verdict") in {"correct", "incorrect", "uncertain"}, upload
            assert upload["problem"]["content_idx"] == MATCHING_CONTENT_IDX, upload
            assert not result["console_errors"], result["console_errors"]
            assert not result["page_errors"], result["page_errors"]
            assert not result["request_failures"], result["request_failures"]
            assert not result["http_errors"], result["http_errors"]
            result["status"] = "PASS"
            context.close()
            browser.close()
    except Exception as error:
        result["status"] = "FAIL"
        result["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    finally:
        result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        (output_dir / "matching-heic-summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8301")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--heic", type=Path, required=True)
    parser.add_argument("--postgres-container", default="kodi-postgres")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--credentials-file", type=Path)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "status": result["status"],
        "matching_task": result.get("matching_task"),
        "heic": result.get("heic"),
        "ai_feedback": result.get("ai_feedback"),
    }, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
