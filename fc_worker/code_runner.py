# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

import json
import logging
import pathlib
import tempfile

import requests

from .api_utils import (
    RUN_CODE_SNIPPET_CMD,
    download_model,
    get_headers,
)
from .assemblies_handler import download_assemblies
from .config import RUNNER_LOGS_ENDPOINT, VERSION
from .sandbox import run_in_sandbox


logger = logging.getLogger(__name__)


def _post_log(access_token: str, payload: dict) -> None:
    try:
        res = requests.post(
            url=RUNNER_LOGS_ENDPOINT,
            headers=get_headers(access_token, include_content_type=True),
            data=json.dumps(payload),
        )
        if not res.ok:
            logger.warning("Failed runner-log post: %s %s", res.status_code, res.text)
    except Exception:
        logger.exception("Failed to post runner-log")


def _error_payload(model_id: str, file_name: str, message: str, attributes: dict) -> dict:
    return {
        "modelId": model_id,
        "type": "ERROR",
        "runnerCommand": RUN_CODE_SNIPPET_CMD,
        "uniqueFileName": file_name,
        "message": message,
        "additionalData": {
            "version": VERSION,
            "attributes": attributes,
        },
    }


def run_code_snippet_command(event: dict, context) -> dict:
    model_id = event.get("id") or ""
    file_name_raw = event.get("fileName")
    access_token = event.get("accessToken") or ""
    script = event.get("script")
    attributes = event.get("attributes") or {}

    if not (model_id and file_name_raw and access_token and script):
        msg = (
            "RUN_CODE_SNIPPET payload missing one of "
            "[id, fileName, accessToken, script]"
        )
        logger.error(msg)
        if access_token and model_id and file_name_raw:
            _post_log(access_token, _error_payload(model_id, file_name_raw, msg, attributes))
        return {"Status": "ERROR", "error": msg}

    file_name = pathlib.Path(file_name_raw)
    if file_name.suffix.upper() != ".FCSTD":
        msg = (
            f"RUN_CODE_SNIPPET only supports .FCStd models; "
            f"got {file_name.suffix!r}"
        )
        logger.error(msg)
        _post_log(access_token, _error_payload(model_id, str(file_name), msg, attributes))
        return {"Status": "ERROR", "error": msg}

    headers = get_headers(access_token)

    with tempfile.TemporaryDirectory(prefix="rcs-") as tmp_dir:
        model_path = pathlib.Path(tmp_dir) / "model.FCStd"
        try:
            download_model(str(file_name), headers, model_path)
            download_assemblies(model_id, model_path, tmp_dir, headers)
        except Exception as ex:
            msg = f"failed to fetch model: {type(ex).__name__}: {ex}"
            logger.exception(msg)
            _post_log(access_token, _error_payload(model_id, str(file_name), msg, attributes))
            return {"Status": "ERROR", "error": msg}

        try:
            result = run_in_sandbox(
                user_script=script,
                model_path=model_path,
            )
        except Exception as ex:
            msg = f"sandbox internal error: {type(ex).__name__}: {ex}"
            logger.exception(msg)
            _post_log(access_token, _error_payload(model_id, str(file_name), msg, attributes))
            return {"Status": "ERROR", "error": msg}

    _post_log(access_token, {
        "modelId": model_id,
        "type": "SUCCESS" if result.exit_code == 0 else "INFO",  # INFO for user-script errors; ERROR is reserved for infra failures
        "runnerCommand": RUN_CODE_SNIPPET_CMD,
        "uniqueFileName": str(file_name),
        "additionalData": {
            "version": VERSION,
            "attributes": attributes,
            "exitCode": result.exit_code,
            "durationMs": result.duration_ms,
            "timedOut": result.timed_out,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "stdoutTruncated": result.truncated_stdout,
            "stderrTruncated": result.truncated_stderr,
            "cgroup": {
                "pidsCapped": result.cgroup_pids_capped,
                "pidsMax": result.cgroup_pids_max,
                "membersSeen": result.cgroup_members_seen,
                "setupError": result.cgroup_attach_error,
            },
        },
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
