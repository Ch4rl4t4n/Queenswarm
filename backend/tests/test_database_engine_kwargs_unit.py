"""Unit tests for async engine construction helpers."""

from sqlalchemy.pool import NullPool

from app.core.database import build_async_engine_kwargs


def test_build_async_engine_kwargs_api_uses_pool() -> None:
    """Operator FastAPI process should keep a bounded connection pool."""

    kwargs = build_async_engine_kwargs(celery_worker=False)
    assert kwargs["pool_size"] == 20
    assert kwargs["max_overflow"] == 10
    assert "poolclass" not in kwargs


def test_build_async_engine_kwargs_celery_uses_null_pool() -> None:
    """Celery tasks call ``asyncio.run`` per task — avoid loop-bound pool connections."""

    kwargs = build_async_engine_kwargs(celery_worker=True)
    assert kwargs["poolclass"] is NullPool
    assert "pool_size" not in kwargs
