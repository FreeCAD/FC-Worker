# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

import logging
import os
import re

import requests
import FreeCAD

from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT, DIRECTORY_ENDPOINT
from .utils.multi_doc_utils import find_missing_links


logger = logging.getLogger(__name__)


STEP_EXTENSIONS = (".step", ".stp", ".STEP", ".STP")


def download_files(file_paths, model_id, directory_path, headers, cache=None, quiet=False):
    cache = {} if cache is None else cache
    log_missing = logger.debug if quiet else logger.error

    def get_value(data, key_path, default=None):
        keys = key_path.split(".")
        val = data
        try:
            for key in keys:
                val = val[key]
            return val
        except (KeyError, TypeError):
            return default

    def get_file_data(files, file_name):
        for _file in files:
            if get_value(_file, "custFileName") == file_name:
                return _file
        return None

    def get_directory_data(directories, dir_name):
        for _dir in directories:
            if get_value(_dir, "name") == dir_name:
                return _dir
        return None

    def download_file(file, output_file_path):

        folder_path = output_file_path.split("/")[:-1]
        if folder_path:
            nested_dir = output_file_path.rsplit("/", 1)[0]
            if not os.path.exists(nested_dir):
                os.makedirs(output_file_path.rsplit("/", 1)[0])

        _file_name = get_value(file, "currentVersion.uniqueFileName")
        res = requests.get(
            url=f"{UPLOAD_ENDPOINT}/{_file_name}",
            headers=headers
        )
        if not res.ok:
            raise Exception("Failed to generate signed url")

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

        with open(output_file_path, "wb") as f:
            f.write(file_data)

    def fetch_or_get_directory(directory_id):
        if directory_id in directories:
            return directories[directory_id]
        directory_resp = requests.get(url=f"{DIRECTORY_ENDPOINT}/{directory_id}", headers=headers)
        if directory_resp.ok:
            directory = directory_resp.json()
            directories[directory_id] = directory
            return directory
        return None

    files_available = []
    files_not_available = []
    directories = cache.setdefault("directories", dict())
    if "model" not in cache:
        model_resp = requests.get(url=f"{MODEL_ENDPOINT}/{model_id}", headers=headers)
        cache["model"] = model_resp.json() if model_resp.ok else None
    model = cache["model"]
    if model is not None:

        for file_path in file_paths:
            file_path_split = file_path.split("/")
            directory_id = get_value(model, "file.directory._id", None)
            if directory_id is None:
                logger.error("File parent directory not found")
                return files_available, file_paths

            is_directory_not_found = False
            if len(file_path_split) > 1:
                for dir_name in file_path_split[:-1]:
                    directory = fetch_or_get_directory(directory_id)
                    if directory is None:
                        logger.error(f"Directory (id: {directory_id} not found")
                        return files_available, file_paths
                    if dir_name == "..":
                        _dir = get_value(directory, "parentDirectory")
                    else:
                        _dir = get_directory_data(get_value(directory, "directories"), dir_name)
                    if _dir is None:
                        log_missing("Directory not found in directory")
                        files_not_available.append(file_path)
                        is_directory_not_found = True
                        break
                    directory_id = get_value(_dir, "_id")
                else:
                    directory = fetch_or_get_directory(directory_id)

            else:
                directory = fetch_or_get_directory(directory_id)
                if directory is None:
                    logger.error("File parent directory not found")
                    return files_available, file_paths

            if is_directory_not_found is False and directory:
                file_name = file_path_split[-1]
                file = get_file_data(get_value(directory, "files"), file_name)
                if file is None:
                    log_missing("File not found in directory")
                    files_not_available.append(file_path)
                else:
                    file_output_path = f"{directory_path}/{file_path}"
                    download_file(file, file_output_path)
                    files_available.append(file_output_path)
    else:
        logger.error(f"Failed to fetch model: {model_id}")
        return files_available, file_paths
    logger.debug(f"Linked files: {str(files_available)}")
    return files_available, files_not_available


def download_links_files(doc, model_id, directory_path, headers):
    linked_files = find_missing_links(doc)
    logger.debug(f"Linked files: {str(linked_files)}")
    files_available, files_not_available = download_files(linked_files, model_id, directory_path, headers)
    return linked_files, files_available, files_not_available


def find_kicad_project_models(board_path):
    """Component model paths a KiCad board expects next to itself, relative to its folder."""
    with open(board_path, "r", encoding="utf-8", errors="replace") as fh:
        references = re.findall(r'\(model\s+"([^"]+)"', fh.read())
    relative = []
    for reference in references:
        reference = reference.replace("\\", "/")
        if reference.startswith("${KIPRJMOD}"):
            reference = reference[len("${KIPRJMOD}"):].lstrip("/")
        elif "${" in reference or reference.startswith(("/", "kicad-embed://")):
            continue
        if reference and reference not in relative:
            relative.append(reference)
    return relative


def download_kicad_models(model_id, input_file, tmp_dir, headers):
    linked_files = []
    files_available = []
    files_not_available = []
    cache = dict()
    try:
        linked_files = find_kicad_project_models(input_file)
        for reference in linked_files:
            # A reference names one file, but the converter accepts any STEP spelling of its stem.
            stem, ext = os.path.splitext(reference)
            candidates = [reference] if ext in STEP_EXTENSIONS else []
            candidates += [stem + e for e in STEP_EXTENSIONS if stem + e != reference]
            for candidate in candidates:
                found, _ = download_files([candidate], model_id, str(tmp_dir), headers, cache, quiet=True)
                if found:
                    files_available.append(found[0])
                    break
            else:
                files_not_available.append(reference)
    except Exception as ex:
        logger.error(str(ex))
    return linked_files, files_available, files_not_available


def download_assemblies(model_id, input_file, tmp_dir, headers):
    linked_files = []
    files_available = []
    files_not_available = []
    doc = None
    try:
        doc = FreeCAD.openDocument(str(input_file))
        FreeCAD.setActiveDocument(doc.Name)
        missing_file = find_missing_links(doc)
        if len(missing_file):
            linked_files, files_available, files_not_available = download_links_files(doc, model_id, str(tmp_dir), headers)
    except Exception as ex:
        logger.error(str(ex))
    finally:
        if doc:
            FreeCAD.closeDocument(doc.Name)
    return linked_files, files_available, files_not_available
