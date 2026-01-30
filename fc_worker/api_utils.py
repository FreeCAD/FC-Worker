# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import json
import requests
import logging
from typing import Optional, Callable

from .errors import ERROR_CODES
from .config import VERSION, RUNNER_LOGS_ENDPOINT, MODEL_ENDPOINT, USER_ENDPOINT


logger = logging.getLogger(__name__)


HEALTH_CHECK_CMD = "health_check"
CONFIGURE_MODEL_CMD = "CONFIGURE_MODEL"
EXPORT_FCSTD_CMD = "EXPORT_FCSTD"
EXPORT_STEP_CMD = "EXPORT_STEP"
EXPORT_STL_CMD = "EXPORT_STL"
EXPORT_OBJ_CMD = "EXPORT_OBJ"
EXPORT_CMDS = [EXPORT_FCSTD_CMD, EXPORT_STEP_CMD, EXPORT_STL_CMD, EXPORT_OBJ_CMD]


def get_headers(access_token: str, include_content_type: bool = False) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def get_model_endpoint(model_id: str, is_shared_model: Optional[bool] = None) -> str:
    if is_shared_model is None:
        return f"{MODEL_ENDPOINT}/{model_id}"
    return f"{MODEL_ENDPOINT}/{model_id}?isSharedModel={str(is_shared_model).lower()}"


def trace_log(func: Callable) -> Callable:
    """Wrapper to trace logs."""
    def _wrapper(event, context):
        access_token = event.get("accessToken")
        model_id = event.get("id", None)
        command = event.get("command", None)
        file_name = event.get("fileName", None)
        is_shared_model = event.get("isSharedModel", None)

        try:
            result = func(event, context)
        except Exception as ex:
            if model_id and command and file_name:
                res = requests.post(
                    url=RUNNER_LOGS_ENDPOINT,
                    headers=get_headers(access_token, True),
                    data=json.dumps({
                        "modelId": model_id,
                        "type": "ERROR",
                        "runnerCommand": command,
                        "uniqueFileName": file_name,
                        "message": f"{type(ex)}: {ex}",
                        "additionalData": {
                            "version": VERSION,
                            "attributes": event.get("attributes", {}),
                        }
                    })
                )

                if res.ok:
                    data_to_patch = {}
                    if command == CONFIGURE_MODEL_CMD:
                        data_to_patch["latestLogErrorIdForObjGenerationCommand"] = res.json()["_id"]
                    elif command == EXPORT_FCSTD_CMD:
                        data_to_patch["latestLogErrorIdForFcstdExportCommand"] = res.json()["_id"]
                    elif command == EXPORT_STEP_CMD:
                        data_to_patch["latestLogErrorIdForStepExportCommand"] = res.json()["_id"]
                    elif command == EXPORT_STL_CMD:
                        data_to_patch["latestLogErrorIdForStlExportCommand"] = res.json()["_id"]
                    elif command == EXPORT_OBJ_CMD:
                        data_to_patch["latestLogErrorIdForObjExportCommand"] = res.json()["_id"]

                    re = requests.patch(
                        url=get_model_endpoint(model_id, is_shared_model),
                        headers=get_headers(access_token, True),
                        data=json.dumps(data_to_patch)
                    )
                    if re.ok:
                        logger.info("Log successfully traced!")
                    else:
                        logger.debug(str(re.text))
                        logger.warning("Got error in tracing log!")

                else:
                    logger.debug(str(res.text))
                    logger.warning("Got error in tracing log!")

            raise ex

        if model_id and command and file_name:
            res = requests.post(
                url=RUNNER_LOGS_ENDPOINT,
                headers=get_headers(access_token, True),
                data=json.dumps({
                    "modelId": model_id,
                    "type": "SUCCESS",
                    "runnerCommand": command,
                    "uniqueFileName": file_name,
                    "additionalData": {
                        "version": VERSION,
                        "attributes": event.get("attributes", {})
                    }
                })
            )
            if res.ok:
                logger.info("Log successfully traced!")
            else:
                logger.debug(str(res.text))
                logger.warning("Got error in tracing log!")
        return result

    return _wrapper


def trace_error_log(func: Callable) -> Callable:
    """Wrapper to trace error in Model"""
    def _wrapper(event, context):
        access_token = event.get("accessToken")
        model_id = event.get("id", None)
        is_shared_model = event.get("isSharedModel", None)
        error_data = None
        result = None
        raise_exception = None
        try:
            result = func(event, context)
        except ERROR_CODES as ex:
            logger.warning(f"Defined Exception occurs: {str(ex)}")
            error_data = ex.as_dict()
        except Exception as ex:
            logger.error(f"Undefined Exception occurs: {str(ex)}")
            raise_exception = ex
            error_data = {
                "code": 999,
                "type": "INTERNAL_SERVER_ERROR",
                "detail": {
                    "error": ex.args,
                    "strError": str(ex)
                },
            }
        if error_data:
            res = requests.patch(
                url=f"{MODEL_ENDPOINT}/{model_id}" if is_shared_model is None else f"{MODEL_ENDPOINT}/{model_id}?isSharedModel={str(is_shared_model).lower()}",
                headers=get_headers(access_token, True),
                data=json.dumps({
                    "isObjGenerationInProgress": False,
                    "isObjGenerated": False,
                    "errorMsg": error_data
                }),
            )
            if res.ok:
                logger.info("Error successfully traced!")
            else:
                logger.debug(str(res.text))
                logger.warning("Got error in tracing log!")

        if raise_exception:
            raise raise_exception

        return result

    return _wrapper


def load_user(event):
    access_token = event.get("accessToken")
    resp = requests.get(
        url=f"{USER_ENDPOINT}/?getOnlyAccessTokenUser=true",
        headers=get_headers(access_token, True)
    )
    if resp.ok:
        users = resp.json()
        if users.get("total"):
            logger.debug("Successfully fetch user details")
            return users["data"][0]
    else:
        logger.warning("Failed to fetch user")
