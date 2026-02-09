# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import pathlib
import tempfile
import json
import logging

import requests
import FreeCAD

from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT, SHARED_MODEL_ENDPOINT
from .assemblies_handler import download_assemblies
from .utils.generic_utils import get_property_bag_obj, get_property_data, update_model, get_app_varset_obj
from .utils.import_utils import open_doc_in_freecad
from .utils.export_utils import export_model


logger = logging.getLogger(__name__)


COMMANDS_EXTENSION = {
    "EXPORT_FCSTD": "FCStd",
    "EXPORT_STEP": "STEP",
    "EXPORT_STL": "STL",
    "EXPORT_OBJ": "OBJ"
}


def export_command(event, command):

    attributes = event.get("attributes", {})

    # Getting signed url to download the file
    _id = event.get("id")
    access_token = event.get("accessToken", None)
    shared_model_id = event.get("sharedModelId", None)
    file_name = pathlib.Path(event.get("fileName"))

    headers = {}
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

    logger.info("Start fetching signed URL from upload endpoint.")
    res = requests.get(
        url=f"{UPLOAD_ENDPOINT}/{file_name}" if access_token else f"{UPLOAD_ENDPOINT}/{file_name}?modelId={_id}",
        headers=headers
    )

    if not res.ok:
        raise Exception("Failed to generate signed url")
    logger.info("Successfully fetched signed URL.")

    # download file from signed url
    res = requests.get(
        url=res.json().get("url"),
    )
    if not res.ok:
        raise Exception("Failed to download file from signed url")
    file_data = b""
    for chunk in res.iter_content(chunk_size=1024):
        if chunk:
            file_data += chunk

    with tempfile.TemporaryDirectory() as tmp_dir:

        output_file = f"{tmp_dir}/{_id}_export.{COMMANDS_EXTENSION[command]}"
        input_file = f"{tmp_dir}/{file_name}"

        with open(input_file, "wb") as f:
            f.write(file_data)

        if pathlib.Path(input_file).suffix.upper() == ".FCSTD":
            download_assemblies(_id, input_file, tmp_dir, headers)
        export_model_cmd(input_file, attributes, output_file)

        logger.info("Starting pushing generated mesh to upload endpoint")
        res = requests.post(
            url=UPLOAD_ENDPOINT if access_token else f"{UPLOAD_ENDPOINT}?modelId={_id}",
            headers=headers,
            files={"file": open(output_file, "rb")}
        )

        if not res.ok:
            raise Exception("Failed to upload generated file")
        logger.info("Successfully pushed generated mesh to upload endpoint")

        model_data = dict()
        if command == "EXPORT_FCSTD":
            model_data["isExportFCStdGenerated"] = True
        elif command == "EXPORT_STEP":
            model_data["isExportSTEPGenerated"] = True
        elif command == "EXPORT_STL":
            model_data["isExportSTLGenerated"] = True
        else:
            model_data["isExportOBJGenerated"] = True

        headers["Content-Type"] = "application/json"

        logger.debug(json.dumps(model_data))

        logger.info("Starting patching status")
        if shared_model_id is None:
            logger.debug(f"Patching to models")
            r = requests.patch(
                url=f"{MODEL_ENDPOINT}/{_id}",
                headers=headers,
                data=json.dumps(model_data),
            )
        else:
            logger.debug(f"Patching to shared-models")
            r = requests.patch(
                url=f"{SHARED_MODEL_ENDPOINT}/{shared_model_id}",
                headers=headers,
                data=json.dumps({"model": model_data}),
            )

        if not r.ok:
            raise Exception("Failed to push status data")

        logger.info("Successfully patched status data endpoint")

    return {"Status": "OK"}


def export_model_cmd(input_file_path: str, attributes: dict, export_file_path: str):
    try:
        doc = open_doc_in_freecad(input_file_path)

        attribute_obj = get_app_varset_obj(doc) or get_property_bag_obj(doc)
        if attribute_obj:
            initial_attributes = get_property_data(attribute_obj)
            if attributes:
                update_model(attribute_obj, initial_attributes, attributes)

        export_model(doc, pathlib.Path(export_file_path))
    finally:
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)
