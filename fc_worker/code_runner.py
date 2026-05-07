# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

import json
import logging
import pathlib
import tempfile
import time

import requests

from .api_utils import (
    download_model,
    get_headers,
)
from .assemblies_handler import download_assemblies
from .config import CODE_RUNS_ENDPOINT
from .sandbox import run_in_sandbox


logger = logging.getLogger(__name__)


def _patch_run(execution_id: str, access_token: str, payload: dict) -> None:
    try:
        res = requests.patch(
            url=f"{CODE_RUNS_ENDPOINT}/{execution_id}",
            headers=get_headers(access_token, include_content_type=True),
            data=json.dumps(payload),
        )
        if not res.ok:
            logger.warning("Failed code-runs patch: %s %s", res.status_code, res.text)
    except Exception:
        logger.exception("Failed to patch code-runs")


def _error_patch(message: str) -> dict:
    return {
        "status": "error",
        "error": message,
        "finishedAt": int(time.time() * 1000),
    }


def run_code_snippet_command(event: dict, context) -> dict:
    execution_id = event.get("executionId") or ""
    file_name_raw = event.get("fileName")
    access_token = event.get("accessToken") or ""
    script = event.get("script")
    model_id = event.get("id") or ""

    if not (execution_id and model_id and file_name_raw and access_token and script):
        logger.error(
            "RUN_CODE_SNIPPET payload missing one of "
            "[id, executionId, fileName, accessToken, script]"
        )
        if execution_id and access_token:
            _patch_run(execution_id, access_token, _error_patch(
                "Internal error. Please contact support."
            ))
        return {"Status": "ERROR"}

    file_name = pathlib.Path(file_name_raw)
    if file_name.suffix.upper() != ".FCSTD":
        logger.error(
            "RUN_CODE_SNIPPET unsupported suffix: %s", file_name.suffix
        )
        _patch_run(execution_id, access_token, _error_patch(
            "Only .FCStd models are supported."
        ))
        return {"Status": "ERROR"}

    # mark as running after input validation
    _patch_run(execution_id, access_token, {
        "status": "running",
        "startedAt": int(time.time() * 1000),
    })

    headers = get_headers(access_token)

    with tempfile.TemporaryDirectory(prefix="rcs-") as tmp_dir:
        model_path = pathlib.Path(tmp_dir) / "model.FCStd"
        try:
            download_model(str(file_name), headers, model_path)
            download_assemblies(model_id, model_path, tmp_dir, headers)
        except Exception as ex:
            logger.exception("failed to fetch model: %s: %s", type(ex).__name__, ex)
            _patch_run(execution_id, access_token, _error_patch(
                "Failed to load the model. Please try again."
            ))
            return {"Status": "ERROR"}

        try:
            result = run_in_sandbox(
                user_script=script,
                model_path=model_path,
            )
        except Exception as ex:
            logger.exception("sandbox internal error: %s: %s", type(ex).__name__, ex)
            _patch_run(execution_id, access_token, _error_patch(
                "Failed to run the script. Please try again."
            ))
            return {"Status": "ERROR"}

    _patch_run(execution_id, access_token, {
        "status": "success",
        "exitCode": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "durationMs": result.duration_ms,
        "finishedAt": int(time.time() * 1000),
    })

    return {
        "Status": "OK",
        "exitCode": result.exit_code,
        "durationMs": result.duration_ms,
        "timedOut": result.timed_out,
        "stdoutBytes": len(result.stdout),
        "stderrBytes": len(result.stderr),
        "cgroupPidsCapped": result.cgroup_pids_capped,
    }
