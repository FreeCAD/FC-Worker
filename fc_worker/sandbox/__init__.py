# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

"""bubblewrap sandbox for safe execution of user-supplied FreeCAD scripts."""

from fc_worker.sandbox.sandbox import (
    DEFAULT_CPU_SECONDS,
    DEFAULT_FSIZE_BYTES,
    DEFAULT_MEMORY_BYTES,
    DEFAULT_NOFILE,
    DEFAULT_NPROC,
    DEFAULT_OUTPUT_BYTES,
    DEFAULT_WALLCLOCK_SECONDS,
    SandboxResult,
    run_in_sandbox,
)
