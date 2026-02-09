# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import logging
import os

import requests
import FreeCAD

from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT, DIRECTORY_ENDPOINT
from .utils.multi_doc_utils import find_missing_links


logger = logging.getLogger(__name__)


def download_links_files(doc, model_id, directory_path, headers):
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
    linked_files = find_missing_links(doc)
    logger.debug(f"Linked files: {str(linked_files)}")
    model_resp = requests.get(url=f"{MODEL_ENDPOINT}/{model_id}", headers=headers)
    directories = dict()
    if model_resp.ok:
        model = model_resp.json()

        for file_path in linked_files:
            file_path_split = file_path.split("/")
            directory_id = get_value(model, "file.directory._id", None)
            if directory_id is None:
                logger.error("File parent directory not found")
                return linked_files, files_available, linked_files

            is_directory_not_found = False
            if len(file_path_split) > 1:
                for dir_name in file_path_split[:-1]:
                    directory = fetch_or_get_directory(directory_id)
                    if directory is None:
                        logger.error(f"Directory (id: {directory_id} not found")
                        return linked_files, files_available, linked_files
                    if dir_name == "..":
                        _dir = get_value(directory, "parentDirectory")
                    else:
                        _dir = get_directory_data(get_value(directory, "directories"), dir_name)
                    if _dir is None:
                        logger.error("Directory not found in directory")
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
                    return linked_files, files_available, linked_files

            if is_directory_not_found is False and directory:
                file_name = file_path_split[-1]
                file = get_file_data(get_value(directory, "files"), file_name)
                if file is None:
                    logger.error("File not found in directory")
                    files_not_available.append(file_path)
                else:
                    file_output_path = f"{directory_path}/{file_path}"
                    download_file(file, file_output_path)
                    files_available.append(file_output_path)
    else:
        logger.error(f"Failed to fetch model: {model_id}")
        return linked_files, files_available, linked_files
    logger.debug(f"Linked files: {str(files_available)}")
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
