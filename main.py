import os

from celery import Celery
from dotenv import load_dotenv
from fastapi import FastAPI
from fc_worker import export_command, model_configurer_command
from fc_worker.api_utils import (
    CONFIGURE_MODEL_CMD,
    EXPORT_CMDS,
    HEALTH_CHECK_CMD,
    trace_log,
)
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

redis_host = os.environ["REDIS_HOST"]
redis_port = os.environ["REDIS_PORT"]

# Configure Celery with Redis from environment variables
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


@app.post("/2015-03-31/functions/function/invocations", status_code=202)
async def start_job(payload: ModelPayload):
    command = payload.command
    if command == HEALTH_CHECK_CMD:
        return {"Status": "OK"}
    elif command.upper() in [CONFIGURE_MODEL_CMD, *EXPORT_CMDS]:
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
    else:
        return f"Invalid command: {command}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
