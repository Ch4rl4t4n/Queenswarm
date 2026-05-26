"""Trigger a supervisor routine by name (operator utility)."""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import select

from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now
from app.core.database import async_session
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


async def main(*, routine_name: str, tenant_id: uuid.UUID | None) -> int:
    async with async_session() as db:
        stmt = select(SupervisorRoutine).where(SupervisorRoutine.name == routine_name)
        if tenant_id is not None:
            stmt = stmt.where(SupervisorRoutine.tenant_id == tenant_id)
        routine = await db.scalar(stmt.limit(1))
        if routine is None:
            print(f"routine_not_found:{routine_name}")
            return 1
        session_id = await trigger_supervisor_routine_now(db, routine=routine)
        await db.commit()
        print(f"session_id={session_id}")
    return 0


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Sentinel daily scan"
    tid = uuid.UUID(sys.argv[2]) if len(sys.argv) > 2 else uuid.UUID("e098b808-8974-4bae-a6e1-de10bf6a2880")
    raise SystemExit(asyncio.run(main(routine_name=name, tenant_id=tid)))
