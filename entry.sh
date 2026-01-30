#!/usr/bin/env sh
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    exec /usr/bin/aws-lambda-rie /usr/bin/python3 -m awslambdaric $1
else
    exec /usr/bin/python3 -m awslambdaric $1
fi