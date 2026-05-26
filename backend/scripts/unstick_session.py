"""One-off operator script: re-approve and requeue a stuck supervisor session."""

from __future__ import annotations

import asyncio
import sys
import uuid

from app.application.services.supervisor.session_service import (
    apply_session_review,
    get_supervisor_session,
)
from app.core.database import async_session


async def main(session_id: uuid.UUID) -> int:
    async with async_session() as db:
        row = await get_supervisor_session(db, session_id)
        if row is None:
            print("session_not_found", file=sys.stderr)
            return 1
        before = dict(row.context_summary or {})
        print(
            f"before status={row.status} approval_required={before.get('approval_required')} "
            f"reason={before.get('approval_reason')!r}"
        )
        await apply_session_review(
            db,
            session_row=row,
            decision="approve",
            note="Re-approve after approve-loop fix",
        )
        await db.commit()
        after = dict(row.context_summary or {})
        print(
            f"after status={row.status} approval_required={after.get('approval_required')} "
            f"requeued={after.get('requeued_sub_agents')}"
        )
    return 0


if __name__ == "__main__":
    sid = uuid.UUID(sys.argv[1] if len(sys.argv) > 1 else "cd7cadd6-5523-40aa-b1bb-feb38b1256dc")
    raise SystemExit(asyncio.run(main(sid)))
