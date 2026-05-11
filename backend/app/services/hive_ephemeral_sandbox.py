"""Ephemeral Docker probe for hive simulation audit (network none, capped resources)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROBED_CMD = ("echo", "queenswarm-sandbox-probe")


@dataclass(frozen=True)
class SandboxProbeResult:
    """Captured output from a one-shot constrained container lifecycle."""

    container_id: str
    stdout: str
    stderr: str
    duration_sec: float


async def run_ephemeral_sandbox_probe(
    *,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    task_id: uuid.UUID | None,
) -> SandboxProbeResult | None:
    """Create and start (-a) a disposable container; always attempt forced removal afterward.

    Host Docker CLI must be available when ``simulation_docker_execution_enabled`` is used;
    failures are logged and swallowed so LangGraph cycles still persist audit rows.

    Args:
        swarm_id: Owning swarm for structured logs.
        workflow_id: Workflow lineage for structured logs.
        task_id: Optional task binding for structured logs.

    Returns:
        Probe payload when create/start succeeds, else ``None``.
    """

    ctx = logger.bind(
        swarm_id=str(swarm_id),
        workflow_id=str(workflow_id),
        task_id=str(task_id) if task_id else "",
    )
    started = time.perf_counter()
    budget = float(settings.simulation_docker_timeout_sec)
    cid: str | None = None

    async def _run_cmd(
        *cmd: str,
        timeout_remaining: float,
    ) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(
                proc.communicate(),
                timeout=max(timeout_remaining, 0.1),
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        rc = proc.returncode if proc.returncode is not None else -1
        return rc, out, err

    try:
        elapsed = time.perf_counter() - started
        create_cmd = (
            "docker",
            "create",
            "--network",
            "none",
            "--read-only",
            "-m",
            "256m",
            "--cpus",
            "0.5",
            settings.simulation_docker_image.strip(),
            *_PROBED_CMD,
        )
        rc_c, out_c, err_c = await _run_cmd(*create_cmd, timeout_remaining=budget - elapsed)
        if rc_c != 0:
            ctx.warning(
                "hive_sandbox.docker_create_failed",
                return_code=rc_c,
                stderr=err_c.decode(errors="replace")[:512],
            )
            return None
        stripped = out_c.decode(errors="replace").strip()
        if not stripped:
            ctx.warning(
                "hive_sandbox.docker_create_empty_id",
                stderr=err_c.decode(errors="replace")[:512],
            )
            return None
        cid = stripped

        elapsed = time.perf_counter() - started
        rc_s, out_s, err_s = await _run_cmd(
            "docker",
            "start",
            "-a",
            cid,
            timeout_remaining=max(budget - elapsed, 0.1),
        )
        stdout_text = out_s.decode(errors="replace")
        stderr_text = err_s.decode(errors="replace")
        duration_sec = time.perf_counter() - started

        if rc_s != 0:
            ctx.warning(
                "hive_sandbox.docker_start_nonzero",
                return_code=rc_s,
                container_id=cid[:48],
                stderr_head=stderr_text[:512],
            )
            return None

        return SandboxProbeResult(
            container_id=cid,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_sec=duration_sec,
        )
    except TimeoutError:
        ctx.warning(
            "hive_sandbox.docker_probe_timeout",
            timeout_sec=budget,
        )
        return None
    except FileNotFoundError:
        ctx.warning("hive_sandbox.docker_cli_missing")
        return None
    except OSError as exc:
        ctx.warning("hive_sandbox.docker_probe_os_error", error=str(exc))
        return None
    finally:
        if cid is not None:
            try:
                elapsed = time.perf_counter() - started
                await _run_cmd(
                    "docker",
                    "rm",
                    "-f",
                    cid,
                    timeout_remaining=max(min(10.0, budget - elapsed), 0.5),
                )
            except TimeoutError:
                ctx.warning(
                    "hive_sandbox.docker_rm_timeout",
                    container_id_head=cid[:48],
                )
            except OSError as exc:
                ctx.warning(
                    "hive_sandbox.docker_rm_failed",
                    error=str(exc),
                    container_id_head=cid[:48],
                )


__all__ = ["SandboxProbeResult", "run_ephemeral_sandbox_probe"]
