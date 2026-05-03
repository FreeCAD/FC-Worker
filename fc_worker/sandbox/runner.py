# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

import contextlib
import os
import sys
import traceback
from pathlib import Path


@contextlib.contextmanager
def _silence_fds():
    # FreeCAD writes warnings to fd 1/2 from C++, bypassing sys.stdout.
    # Drop everything so only the user script's output reaches the caller.
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out, saved_err = os.dup(1), os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)
        os.close(devnull)


def main(argv):
    if len(argv) != 3:
        print("usage: runner.py <script> <model>", file=sys.stderr)
        return 2

    script_path, model_path = argv[1], argv[2]

    # FreeCAD.so lives in /usr/local/lib, absent from sys.path under python3 -I.
    if "/usr/local/lib" not in sys.path:
        sys.path.insert(0, "/usr/local/lib")

    try:
        with _silence_fds():
            import FreeCAD
            doc = FreeCAD.openDocument(model_path)
    except Exception as ex:
        print(f"[runner] init failed: {type(ex).__name__}: {ex}", file=sys.stderr)
        return 3

    user_code = Path(script_path).read_text()

    user_globals = {
        "__name__": "__user__",
        "__builtins__": __builtins__,
        "FreeCAD": FreeCAD,
        "doc": doc,
    }

    try:
        compiled = compile(user_code, "<user-snippet>", "exec")
        exec(compiled, user_globals)
    except SystemExit as ex:
        return int(ex.code or 0)
    except BaseException as ex:
        # Drop our own runner.py frames so the traceback starts at the
        # user's snippet — sandbox internals are not actionable for users.
        tb = ex.__traceback__
        while tb is not None and tb.tb_frame.f_code.co_filename != "<user-snippet>":
            tb = tb.tb_next
        traceback.print_exception(type(ex), ex, tb)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
