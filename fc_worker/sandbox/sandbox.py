# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

import dataclasses
import os
import resource
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional


DEFAULT_CPU_SECONDS = 10  # max CPU time; kills runaway computation
DEFAULT_WALLCLOCK_SECONDS = 15  # real-clock deadline; always >= CPU limit
DEFAULT_MEMORY_BYTES = 1024 * 1024 * 1024  # virtual address space
DEFAULT_FSIZE_BYTES = 50 * 1024 * 1024  # max single file write inside /work
DEFAULT_NPROC = 16  # cgroup pids.max
DEFAULT_NOFILE = 64  # open file descriptors
DEFAULT_OUTPUT_BYTES = 256 * 1024  # stdout/stderr truncation before runner-log storage

DEFAULT_RUNNER_PATH = Path(__file__).resolve().parent / "runner.py"


@dataclasses.dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    truncated_stdout: bool
    truncated_stderr: bool
    cgroup_pids_capped: bool = False
    cgroup_attach_error: Optional[str] = None
    cgroup_members_seen: int = 0
    cgroup_pids_max: Optional[str] = None


class _PidsCgroup:
    # cgroup v2 pids.max cap — reliable fork-bomb guard.
    # RLIMIT_NPROC is checked against the outer uid inside a user namespace,
    # so the kernel pids controller is the only reliable control here.
    #
    # Layout (set up lazily on first use):
    #   <origin>/            — Docker's namespaced cgroup root
    #   ├── sandbox-host/    — residence for the worker process between jobs
    #   └── sandbox-<id>/    — per-job cap; created and destroyed each run
    #
    # Two cgroups are needed because cgroup v2's "no internal processes" rule
    # prevents enabling +pids on origin while we're still in it. Moving
    # ourselves to sandbox-host first vacates origin, allowing +pids, and
    # per-job sandboxes then work as sibling leaves.

    ROOT = Path("/sys/fs/cgroup")
    _HOST_NAME = "sandbox-host"

    _siblings_root: Optional[Path] = None
    _host_path: Optional[Path] = None
    _setup_error: Optional[str] = None

    @classmethod
    def available(cls) -> bool:
        ctrls = cls.ROOT / "cgroup.controllers"
        try:
            return ctrls.exists() and "pids" in ctrls.read_text().split()
        except OSError:
            return False

    def __init__(self, pids_max: int) -> None:
        self.pids_max = pids_max
        self.path: Optional[Path] = None
        self._enter_error: Optional[str] = None

    @staticmethod
    def _self_cgroup_path() -> Path:
        try:
            for line in Path("/proc/self/cgroup").read_text().splitlines():
                if line.startswith("0::"):  # cgroup v2 unified format
                    return _PidsCgroup.ROOT / line[3:].lstrip("/")
        except OSError:
            pass
        return _PidsCgroup.ROOT

    @classmethod
    def _setup_once(cls) -> None:
        if cls._siblings_root is not None:
            return  # already set up; vacation + +pids only need to happen once

        if not cls.available():
            cls._setup_error = "pids controller not available at /sys/fs/cgroup"
            return

        try:
            origin = cls._self_cgroup_path()
            host = origin / cls._HOST_NAME

            try:
                host.mkdir()
            except FileExistsError:
                pass

            # Vacate ALL origin pids into sandbox-host before enabling
            # +pids (cgroup v2 no-internal-processes rule).
            for pid in (origin / "cgroup.procs").read_text().split():
                try:
                    (host / "cgroup.procs").write_text(pid)
                except OSError:
                    pass  # process exited or kernel won't move it; best effort

            subtree = origin / "cgroup.subtree_control"
            try:
                if "pids" not in subtree.read_text().split():
                    subtree.write_text("+pids")
            except OSError:
                # EBUSY/EINVAL means +pids was already enabled by the orchestrator.
                if "pids" not in subtree.read_text().split():
                    raise

            cls._siblings_root = origin
            cls._host_path = host
            cls._setup_error = None  # clear any prior transient error
        except OSError as ex:
            cls._setup_error = f"{type(ex).__name__}: {ex}"

    def __enter__(self) -> "_PidsCgroup":
        self._setup_once()
        if self._siblings_root is None or self._host_path is None:
            self._enter_error = self._setup_error or "cgroup setup unavailable"
            return self

        candidate = self._siblings_root / f"sandbox-{uuid.uuid4().hex[:12]}"
        try:
            candidate.mkdir()
        except OSError as ex:
            self._enter_error = f"mkdir({candidate}) failed: {type(ex).__name__}: {ex}"
            return self

        try:
            (candidate / "pids.max").write_text(str(self.pids_max))
        except OSError as ex:
            self._enter_error = f"pids.max write failed: {type(ex).__name__}: {ex}"
            try:
                candidate.rmdir()
            except OSError:
                pass
            return self

        # Move ourselves into the per-job leaf; the next Popen fork inherits
        # membership and is capped by pids.max.
        try:
            (candidate / "cgroup.procs").write_text(str(os.getpid()))
        except OSError as ex:
            self._enter_error = (
                f"cgroup.procs write to {candidate} failed: "
                f"{type(ex).__name__}: {ex}"
            )
            try:
                candidate.rmdir()
            except OSError:
                pass
            return self

        self.path = candidate
        return self

    @property
    def applied(self) -> bool:
        return self.path is not None

    def members(self) -> list:
        if self.path is None:
            return []
        try:
            return [int(x) for x in (self.path / "cgroup.procs").read_text().split()]
        except OSError:
            return []

    def setup_error(self) -> Optional[str]:
        return self._enter_error or self._setup_error

    def read_pids_max(self) -> Optional[str]:
        if self.path is None:
            return None
        try:
            return (self.path / "pids.max").read_text().strip()
        except OSError:
            return None

    def __exit__(self, *_) -> None:
        if self.path is None:
            return
        if self._host_path is not None:
            try:
                (self._host_path / "cgroup.procs").write_text(str(os.getpid()))
            except OSError:
                pass
        try:
            (self.path / "cgroup.kill").write_text("1")
        except OSError:
            pass
        for _ in range(50):
            try:
                self.path.rmdir()
                return
            except OSError:
                time.sleep(0.05)


def _rlimit_preexec(cpu_seconds, memory_bytes, fsize_bytes, nproc, nofile):
    """Return a callable for Popen's preexec_fn that applies rlimits and sets
    PR_SET_NO_NEW_PRIVS (blocks setuid privilege escalation) in the child
    process after fork but before exec."""

    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (nproc, nproc))
        resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        try:
            import ctypes

            PR_SET_NO_NEW_PRIVS = 38
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
        except Exception:
            pass

    return apply


def _build_bwrap_argv(
    scratch_dir,
    runner_path,
    script_path,
    model_path,
    cpu_seconds,
    memory_bytes,
    fsize_bytes,
    nproc,
    nofile,
):
    """Build the bwrap + prlimit + python argv list.

    prlimit re-applies rlimits inside bwrap's user namespace, where the
    preexec_fn values set by the parent may not be inherited faithfully."""
    return [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/sbin", "/sbin",
        "--ro-bind", "/etc", "/etc",
        "--ro-bind", "/app", "/app",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--tmpfs", "/run",
        "--bind", str(scratch_dir), "/work",
        "--chdir", "/work",
        "--uid", "65534",
        "--gid", "65534",
        "--clearenv",
        "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/work",
        "--setenv", "LANG", "C.UTF-8",
        "--",
        "/usr/bin/prlimit",
        f"--cpu={cpu_seconds}",
        f"--as={memory_bytes}",
        f"--fsize={fsize_bytes}",
        f"--nproc={nproc}",
        f"--nofile={nofile}",
        "--core=0",
        "--",
        "/usr/bin/python3",
        "-I",  # isolated: no PYTHON*, no user site, no cwd on sys.path
        str(runner_path),
        str(script_path),
        str(model_path),
    ]


def _drain_capped(stream, cap):
    # Read until EOF, keeping at most `cap` bytes. Continues draining past
    # the cap (discarding) so the writer never blocks on a full pipe — that
    # would let a chatty snippet deadlock the parent.
    buf = bytearray()
    truncated = False
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            if len(buf) >= cap:
                truncated = True
                continue
            room = cap - len(buf)
            if len(chunk) > room:
                buf.extend(chunk[:room])
                truncated = True
            else:
                buf.extend(chunk)
    except (OSError, ValueError):
        pass
    return bytes(buf), truncated


def _capture_bounded(proc, max_bytes, timeout, on_timeout):
    out_slot = [b"", False]
    err_slot = [b"", False]

    def _drain(stream, slot):
        slot[0], slot[1] = _drain_capped(stream, max_bytes)

    t_out = threading.Thread(target=_drain, args=(proc.stdout, out_slot), daemon=True)
    t_err = threading.Thread(target=_drain, args=(proc.stderr, err_slot), daemon=True)
    t_out.start()
    t_err.start()

    try:
        proc.wait(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        on_timeout()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    # Pipes close when proc exits; drain threads finish naturally.
    t_out.join(timeout=5)
    t_err.join(timeout=5)
    return out_slot[0], err_slot[0], out_slot[1], err_slot[1], timed_out, proc.returncode


def run_in_sandbox(
    user_script: str,
    model_path: Path,
    *,
    runner_path: Path = DEFAULT_RUNNER_PATH,
    cpu_seconds: int = DEFAULT_CPU_SECONDS,
    wallclock_seconds: int = DEFAULT_WALLCLOCK_SECONDS,
    memory_bytes: int = DEFAULT_MEMORY_BYTES,
    fsize_bytes: int = DEFAULT_FSIZE_BYTES,
    nproc: int = DEFAULT_NPROC,
    nofile: int = DEFAULT_NOFILE,
    max_output_bytes: int = DEFAULT_OUTPUT_BYTES,
) -> SandboxResult:
    """Run user_script under bwrap and return a SandboxResult."""
    scratch = Path(tempfile.mkdtemp(prefix="sbx-"))
    try:
        (scratch / "user_script.py").write_text(user_script)
        shutil.copytree(model_path.parent, scratch / "model")
        sandbox_model = Path("/work/model") / model_path.name

        argv = _build_bwrap_argv(
            scratch_dir=scratch,
            runner_path=runner_path,
            script_path=Path("/work/user_script.py"),
            model_path=sandbox_model,
            cpu_seconds=cpu_seconds,
            memory_bytes=memory_bytes,
            fsize_bytes=fsize_bytes,
            nproc=nproc,
            nofile=nofile,
        )

        start = time.monotonic()
        timed_out = False
        cgroup_ctx = _PidsCgroup(nproc)
        cgroup_ctx.__enter__()
        try:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={},
                preexec_fn=_rlimit_preexec(
                    cpu_seconds,
                    memory_bytes,
                    fsize_bytes,
                    nproc,
                    nofile,
                ),
                start_new_session=True,
            )
        except BaseException:
            cgroup_ctx.__exit__(None, None, None)
            raise

        members_seen = [0]

        def _watch_cgroup():
            while proc.poll() is None:
                n = len(cgroup_ctx.members())
                if n > members_seen[0]:
                    members_seen[0] = n
                time.sleep(0.05)

        watcher = None
        if cgroup_ctx.applied:
            watcher = threading.Thread(target=_watch_cgroup, daemon=True)
            watcher.start()

        def _kill_on_timeout():
            if cgroup_ctx.applied:
                try:
                    (cgroup_ctx.path / "cgroup.kill").write_text("1")
                except OSError:
                    pass
            else:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass

        try:
            (stdout, stderr,
             truncated_stdout, truncated_stderr,
             timed_out, exit_code) = _capture_bounded(
                proc, max_output_bytes, wallclock_seconds, _kill_on_timeout
            )
            if timed_out:
                stderr = stderr + b"\n[sandbox] WALLCLOCK_EXCEEDED\n"
                exit_code = -signal.SIGKILL
        finally:
            cgroup_setup_err = cgroup_ctx.setup_error()
            pids_max_str = cgroup_ctx.read_pids_max()
            if watcher is not None:
                watcher.join(timeout=0.5)
            cgroup_ctx.__exit__(None, None, None)

        duration_ms = int((time.monotonic() - start) * 1000)

        return SandboxResult(
            exit_code=exit_code,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            duration_ms=duration_ms,
            timed_out=timed_out,
            truncated_stdout=truncated_stdout,
            truncated_stderr=truncated_stderr,
            cgroup_pids_capped=cgroup_ctx.applied,
            cgroup_attach_error=cgroup_setup_err,
            cgroup_members_seen=members_seen[0],
            cgroup_pids_max=pids_max_str,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
