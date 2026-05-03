# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2025 Amritpal Singh <amrit3701@gmail.com>

import os

from celery import Celery
from dotenv import load_dotenv
from fastapi import FastAPI
from fc_worker import (
    export_command,
    model_configurer_command,
    run_code_snippet_command,
)
from fc_worker.api_utils import (
    CONFIGURE_MODEL_CMD,
    EXPORT_CMDS,
    HEALTH_CHECK_CMD,
    RUN_CODE_SNIPPET_CMD,
    trace_log,
)
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

redis_host = os.environ["REDIS_HOST"]
redis_port = os.environ["REDIS_PORT"]
redis_password = os.environ.get("REDIS_PASSWORD", "")
redis_username = os.environ.get("REDIS_USERNAME", "default")

# Configure Celery with Redis from environment variables
if redis_password:
    broker_url = result_backend = f"redis://{redis_username}:{redis_password}@{redis_host}:{redis_port}/0"
else:
    broker_url = result_backend = f"redis://{redis_host}:{redis_port}/0"
celery = Celery(__name__, broker=broker_url, backend=result_backend)


class ModelPayload(BaseModel):
    id: str | None = None
    fileName: str | None = None
    command: str
    accessToken: str | None = None
    attributes: dict = {}
    isSharedModel: bool | None = None
    sharedModelId: str | None = None
    script: str | None = None


@app.post("/2015-03-31/functions/function/invocations", status_code=202)
async def start_job(payload: ModelPayload):
    command = payload.command
    if command == HEALTH_CHECK_CMD:
        return {"Status": "OK"}
    elif command.upper() in [CONFIGURE_MODEL_CMD, *EXPORT_CMDS, RUN_CODE_SNIPPET_CMD]:
        run_background_task.delay(payload.model_dump())
        return {"Status": "Job started"}
    else:
        return f"Thank you strace, worker is running."


@celery.task
def run_background_task(payload):
    print(f"Processing job with payload: {payload}")
    result = lambda_handler(payload, {})
    print(f"Completed processing job with payload: {payload} And result: {result}")


@trace_log
def lambda_handler(event, context):
    print(f"Starting job for event: {event}")
    command = event.get("command", None)
    if command.upper() == CONFIGURE_MODEL_CMD:
        return model_configurer_command(event, context)
    elif command.upper() in EXPORT_CMDS:
        export_command(event, command)
    elif command.upper() == RUN_CODE_SNIPPET_CMD:
        return run_code_snippet_command(event, context)
    else:
        return f"Invalid command: {command}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
