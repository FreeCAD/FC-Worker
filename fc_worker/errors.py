# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

class WorkerError(BaseException):
    code = None
    type = None

    def __str__(self):
        return f"Error {self.code} ({self.type}): {self.args}"

    def as_dict(self):
        return {
            "code": self.code,
            "type": self.type,
            "detail": self.args[0] if len(self.args) else {},
        }


class MissingAssembliesError(WorkerError):
    code = 101
    type = "MISSING_ASSEMBLIES_ERROR"


class UserNotAllowedToRecomputeAssembliesError(WorkerError):
    code = 102
    type = "USER_NOT_ALLOWED_TO_RECOMPUTE_ASSEMBLIES_ERROR"


ERROR_CODES = (MissingAssembliesError, UserNotAllowedToRecomputeAssembliesError, )
