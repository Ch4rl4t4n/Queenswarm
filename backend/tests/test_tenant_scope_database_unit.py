"""Unit tests for automatic tenant scope hooks in database layer."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from sqlalchemy import select

from app.core.database import _apply_tenant_scope, _autofill_tenant_id
from app.core.tenant_context import set_current_tenant_id
from app.infrastructure.persistence.models.task import Task


def test_apply_tenant_scope_when_context_present_then_statement_has_tenant_predicate() -> None:
    """Tenant hook injects tenant criterion for tenant-scoped ORM entities."""

    tenant_id = uuid.uuid4()
    set_current_tenant_id(tenant_id)
    state = SimpleNamespace(is_select=True, statement=select(Task))
    _apply_tenant_scope(state)
    sql = str(state.statement)
    assert "tenant_id" in sql
    set_current_tenant_id(None)


def test_autofill_tenant_id_when_new_tenant_scoped_rows_then_assigns_context_tenant() -> None:
    """before_flush hook auto-populates tenant_id for new tenant-scoped rows."""

    tenant_id = uuid.uuid4()
    set_current_tenant_id(tenant_id)

    class _Scoped:
        __tenant_scoped__ = True

        def __init__(self) -> None:
            self.tenant_id = None

    row = _Scoped()
    session = SimpleNamespace(new=[row])
    _autofill_tenant_id(session, None, None)
    assert row.tenant_id == tenant_id
    set_current_tenant_id(None)
