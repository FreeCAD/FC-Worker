# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import os

VERSION = "1.17"

BACKEND_URL = os.getenv("BACKEND_URL")
UPLOAD_ENDPOINT = f"{BACKEND_URL}/upload"
MODEL_ENDPOINT = f"{BACKEND_URL}/models"
SHARED_MODEL_ENDPOINT = f"{BACKEND_URL}/shared-models"
RUNNER_LOGS_ENDPOINT = f"{BACKEND_URL}/runner-logs"
DIRECTORY_ENDPOINT = f"{BACKEND_URL}/directories"
USER_ENDPOINT = f"{BACKEND_URL}/users"
