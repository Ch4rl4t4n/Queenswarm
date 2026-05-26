"""Paper trading bee — simulated quotes, signals, fills, and P&L (no live broker)."""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_json, set_json
from app.domain.external.managers.trading_manager import TradingManager
from app.infrastructure.persistence.models.external_project import ExternalProject
from app.infrastructure.persistence.models.paper_trading import PaperTradingAccount, PaperTradingFill

logger = get_logger(__name__)

_BASE_PRICES_USD: dict[str, float] = {
    "BTC": 95_000.0,
    "ETH": 3_500.0,
    "SOL": 140.0,
    "AVAX": 35.0,
    "LINK": 18.0,
}

_QUOTE_CACHE_PREFIX = "paper_trading:quote:"


def _d(value: float | Decimal) -> Decimal:
    return Decimal(str(value))


async def _simulate_quote(symbol: str) -> float:
    """Return a random-walk proxy price stored briefly in Redis."""

    sym = symbol.strip().upper()
    base = _BASE_PRICES_USD.get(sym, 100.0)
    key = f"{_QUOTE_CACHE_PREFIX}{sym}"
    cached = await get_json(key)
    prev = float(cached.get("price")) if isinstance(cached, dict) and "price" in cached else base
    drift = random.uniform(-0.006, 0.006)
    price = max(0.01, prev * (1.0 + drift))
    await set_json(key, {"price": price, "symbol": sym}, ttl=3600)
    return price


def _project_settings(project: ExternalProject) -> dict[str, Any]:
    raw = project.settings if isinstance(project.settings, dict) else {}
    return dict(raw)


def _is_paper_project(project: ExternalProject) -> bool:
    if project.project_kind != "trading":
        return False
    mode = str(_project_settings(project).get("trading_mode") or "paper").lower()
    return mode == "paper"


async def get_or_create_account(
    session: AsyncSession,
    *,
    project: ExternalProject,
) -> PaperTradingAccount:
    """Ensure a paper ledger exists for the trading project."""

    exec_result = await session.execute(
        select(PaperTradingAccount).where(PaperTradingAccount.project_id == project.id),
    )
    row = exec_result.scalar_one_or_none()
    if row is not None:
        return row

    settings_blob = _project_settings(project)
    watchlist_raw = settings_blob.get("watchlist")
    watchlist = [str(s).upper() for s in watchlist_raw] if isinstance(watchlist_raw, list) else ["BTC", "ETH"]
    starting = float(settings_blob.get("starting_cash_usd") or settings.paper_trading_default_cash_usd)

    row = PaperTradingAccount(
        tenant_id=project.tenant_id,
        project_id=project.id,
        cash_usd=_d(starting),
        starting_cash_usd=_d(starting),
        watchlist=watchlist,
    )
    session.add(row)
    await session.flush()
    return row


async def _reset_daily_pnl_if_needed(account: PaperTradingAccount) -> None:
    """Roll daily P&L bucket at UTC midnight."""

    now = datetime.now(tz=UTC)
    reset_at = account.daily_pnl_reset_at
    if reset_at is not None:
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=UTC)
        if reset_at.date() == now.date():
            return
    account.daily_realized_pnl_usd = _d(0)
    account.daily_pnl_reset_at = now
    if account.is_halted and account.halt_reason and "daily stop-loss" in account.halt_reason.lower():
        account.is_halted = False
        account.halt_reason = None


async def compute_positions(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> dict[str, dict[str, float]]:
    """Aggregate open quantities and average cost from fill history."""

    exec_result = await session.execute(
        select(PaperTradingFill).where(PaperTradingFill.account_id == account_id).order_by(PaperTradingFill.created_at),
    )
    fills = list(exec_result.scalars().all())
    positions: dict[str, dict[str, float]] = {}
    for fill in fills:
        sym = fill.symbol.upper()
        qty = float(fill.quantity)
        signed = qty if fill.side.lower() == "buy" else -qty
        slot = positions.setdefault(sym, {"quantity": 0.0, "cost_basis_usd": 0.0})
        slot["quantity"] += signed
        if fill.side.lower() == "buy":
            slot["cost_basis_usd"] += float(fill.notional_usd)
        elif fill.side.lower() == "sell" and slot["quantity"] >= 0:
            slot["cost_basis_usd"] = max(0.0, slot["cost_basis_usd"] - float(fill.notional_usd))
    return {k: v for k, v in positions.items() if abs(v["quantity"]) > 1e-12}


async def build_portfolio_snapshot(
    session: AsyncSession,
    *,
    project: ExternalProject,
) -> dict[str, Any]:
    """Return P&L snapshot for dashboards."""

    account = await get_or_create_account(session, project=project)
    positions_raw = await compute_positions(session, account_id=account.id)
    positions: list[dict[str, Any]] = []
    unrealized = 0.0
    for symbol, slot in positions_raw.items():
        px = await _simulate_quote(symbol)
        qty = slot["quantity"]
        mv = qty * px
        cost = slot["cost_basis_usd"]
        u_pnl = mv - cost if qty >= 0 else 0.0
        unrealized += u_pnl
        positions.append(
            {
                "symbol": symbol,
                "quantity": round(qty, 8),
                "mark_price_usd": round(px, 4),
                "market_value_usd": round(mv, 2),
                "unrealized_pnl_usd": round(u_pnl, 2),
            },
        )

    equity = float(account.cash_usd) + sum(p["market_value_usd"] for p in positions if p["quantity"] > 0)
    total_pnl = equity - float(account.starting_cash_usd)

    exec_result = await session.execute(
        select(PaperTradingFill)
        .where(PaperTradingFill.project_id == project.id)
        .order_by(desc(PaperTradingFill.created_at))
        .limit(12),
    )
    recent = list(exec_result.scalars().all())

    return {
        "project_id": str(project.id),
        "project_slug": project.slug,
        "display_name": project.display_name,
        "mode": "paper",
        "cash_usd": float(account.cash_usd),
        "starting_cash_usd": float(account.starting_cash_usd),
        "equity_usd": round(equity, 2),
        "realized_pnl_usd": float(account.realized_pnl_usd),
        "daily_realized_pnl_usd": float(account.daily_realized_pnl_usd),
        "unrealized_pnl_usd": round(unrealized, 2),
        "total_pnl_usd": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / float(account.starting_cash_usd)) * 100.0, 2)
        if float(account.starting_cash_usd) > 0
        else 0.0,
        "is_halted": account.is_halted,
        "halt_reason": account.halt_reason,
        "last_tick_at": account.last_tick_at.isoformat() if account.last_tick_at else None,
        "positions": positions,
        "recent_fills": [
            {
                "id": str(f.id),
                "symbol": f.symbol,
                "side": f.side,
                "quantity": float(f.quantity),
                "fill_price_usd": float(f.fill_price_usd),
                "notional_usd": float(f.notional_usd),
                "confidence": float(f.confidence),
                "signal_note": f.signal_note,
                "created_at": f.created_at.isoformat(),
            }
            for f in recent
        ],
        "disclaimer": "Paper trading simulation — not financial advice. No real money at risk.",
    }


async def _maybe_halt_on_daily_loss(account: PaperTradingAccount, project_settings: dict[str, Any]) -> bool:
    max_daily_loss = float(project_settings.get("max_daily_loss_usd") or 500.0)
    if float(account.daily_realized_pnl_usd) <= -abs(max_daily_loss):
        account.is_halted = True
        account.halt_reason = f"Daily stop-loss hit ({account.daily_realized_pnl_usd} USD)."
        return True
    return False


async def _record_fill(
    session: AsyncSession,
    *,
    account: PaperTradingAccount,
    project: ExternalProject,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    confidence: float,
    signal_note: str,
) -> PaperTradingFill | None:
    """Persist fill after TradingManager risk gate passes."""

    from app.application.services.trading_risk_validator import TradingRiskInput, validate_trading_risk

    project_settings = _project_settings(project)
    notional = quantity * price
    risk = validate_trading_risk(
        TradingRiskInput(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price_usd=price,
            confidence=confidence,
            notional_usd=notional,
            is_halted=account.is_halted,
            halt_reason=account.halt_reason,
            daily_realized_pnl_usd=float(account.daily_realized_pnl_usd),
        ),
        project_settings=project_settings,
    )
    if not risk.allowed:
        logger.info(
            "paper_trading.risk_blocked",
            project_id=str(project.id),
            symbol=symbol,
            reasons=risk.reasons,
        )
        return None

    mgr = TradingManager()
    outcome = await mgr.handle(
        action="execute_trade",
        payload={
            "symbol": symbol,
            "quantity": quantity,
            "assumed_price_usd": price,
            "notional_usd": notional,
        },
        project_settings=_project_settings(project),
    )
    if outcome.get("status") != "simulated_fill":
        logger.info(
            "paper_trading.fill_blocked",
            project_id=str(project.id),
            symbol=symbol,
            outcome=outcome,
        )
        return None

    fees = notional * (float(settings.paper_trading_fee_bps) / 10_000.0)
    realized_delta = 0.0
    positions = await compute_positions(session, account_id=account.id)
    pos = positions.get(symbol.upper(), {"quantity": 0.0, "cost_basis_usd": 0.0})

    if side.lower() == "buy":
        if float(account.cash_usd) < notional + fees:
            return None
        account.cash_usd = _d(float(account.cash_usd) - notional - fees)
    else:
        if pos["quantity"] < quantity - 1e-12:
            return None
        avg_cost = pos["cost_basis_usd"] / pos["quantity"] if pos["quantity"] else price
        realized_delta = (price - avg_cost) * quantity - fees
        account.cash_usd = _d(float(account.cash_usd) + notional - fees)
        account.realized_pnl_usd = _d(float(account.realized_pnl_usd) + realized_delta)
        account.daily_realized_pnl_usd = _d(float(account.daily_realized_pnl_usd) + realized_delta)

    fill = PaperTradingFill(
        tenant_id=project.tenant_id,
        project_id=project.id,
        account_id=account.id,
        symbol=symbol.upper(),
        side=side.lower(),
        quantity=_d(quantity),
        fill_price_usd=_d(price),
        fees_usd=_d(fees),
        notional_usd=_d(notional),
        confidence=_d(confidence),
        signal_note=signal_note[:2000],
        verified=True,
    )
    session.add(fill)
    await session.flush()
    return fill


async def run_paper_trading_tick_for_project(
    session: AsyncSession,
    *,
    project: ExternalProject,
) -> dict[str, Any]:
    """Evaluate watchlist symbols and maybe place one paper trade."""

    if not settings.paper_trading_enabled or not _is_paper_project(project) or not project.is_active:
        return {"status": "skipped", "reason": "inactive_or_disabled"}

    account = await get_or_create_account(session, project=project)
    await _reset_daily_pnl_if_needed(account)
    project_settings = _project_settings(project)

    if account.is_halted or await _maybe_halt_on_daily_loss(account, project_settings):
        account.last_tick_at = datetime.now(tz=UTC)
        return {"status": "halted", "reason": account.halt_reason}

    watchlist = [str(s).upper() for s in (account.watchlist or [])][:8]
    if not watchlist:
        watchlist = ["BTC", "ETH"]

    threshold = float(project_settings.get("confidence_threshold") or settings.paper_trading_confidence_threshold)
    max_risk_pct = float(project_settings.get("max_risk_pct_per_trade") or 2.0)
    max_order_usd = float(project_settings.get("max_order_usd") or 2_500.0)
    risk_budget = min(max_order_usd, float(account.cash_usd) * (max_risk_pct / 100.0))

    best: tuple[float, str, str, float, str] | None = None
    for symbol in watchlist:
        price = await _simulate_quote(symbol)
        signal_key = f"paper_trading:signal:{project.id}:{symbol}"
        prior = await get_json(signal_key)
        prior_px = float(prior.get("price")) if isinstance(prior, dict) and "price" in prior else price
        move = (price - prior_px) / prior_px if prior_px else 0.0
        await set_json(signal_key, {"price": price}, ttl=int(timedelta(hours=6).total_seconds()))

        confidence = min(0.99, abs(move) * 120.0)
        if confidence < threshold:
            continue
        side = "buy" if move > 0 else "sell"
        note = f"momentum {move * 100:.2f}% vs prior tick"
        if best is None or confidence > best[0]:
            best = (confidence, symbol, side, price, note)

    account.last_tick_at = datetime.now(tz=UTC)
    if best is None:
        return {"status": "no_signal", "project_id": str(project.id)}

    confidence, symbol, side, price, note = best
    qty = max(0.0001, risk_budget / price)
    fill = await _record_fill(
        session,
        account=account,
        project=project,
        symbol=symbol,
        side=side,
        quantity=qty,
        price=price,
        confidence=confidence,
        signal_note=note,
    )
    await _maybe_halt_on_daily_loss(account, project_settings)

    if fill is not None:
        try:
            from app.application.services.trade_to_content import create_publish_draft_from_paper_fill

            await create_publish_draft_from_paper_fill(session, fill=fill, project=project)
        except Exception as content_exc:  # noqa: BLE001
            logger.warning(
                "paper_trading.trade_to_content_failed",
                project_id=str(project.id),
                error=str(content_exc)[:200],
            )
        try:
            from app.application.services.trading_cockpit_notify import notify_trading_paper_fill

            await notify_trading_paper_fill(
                session,
                fill=fill,
                project=project,
                dashboard_user_id=project.owner_dashboard_user_id,
            )
        except Exception as notify_exc:  # noqa: BLE001
            logger.warning(
                "paper_trading.notify_failed",
                project_id=str(project.id),
                error=str(notify_exc)[:200],
            )

    logger.info(
        "paper_trading.tick_complete",
        project_id=str(project.id),
        symbol=symbol,
        side=side,
        confidence=confidence,
        filled=fill is not None,
    )
    return {
        "status": "filled" if fill is not None else "blocked",
        "project_id": str(project.id),
        "symbol": symbol,
        "side": side,
        "confidence": confidence,
        "fill_id": str(fill.id) if fill else None,
    }


async def list_paper_trading_projects(session: AsyncSession) -> list[ExternalProject]:
    """Return active paper-mode trading external projects."""

    exec_result = await session.execute(
        select(ExternalProject).where(
            ExternalProject.project_kind == "trading",
            ExternalProject.is_active.is_(True),
        ),
    )
    rows = list(exec_result.scalars().all())
    return [row for row in rows if _is_paper_project(row)]


async def run_paper_trading_tick_all(session: AsyncSession) -> dict[str, Any]:
    """Run paper tick across all eligible projects."""

    projects = await list_paper_trading_projects(session)
    results: list[dict[str, Any]] = []
    for project in projects:
        settings_blob = _project_settings(project)
        if settings_blob.get("paper_trading_auto_tick") is False:
            continue
        results.append(await run_paper_trading_tick_for_project(session, project=project))
    return {"projects": len(projects), "results": results}


async def build_dashboard_paper_summary(session: AsyncSession) -> dict[str, Any]:
    """Aggregate paper P&L for queen dashboard widget."""

    projects = await list_paper_trading_projects(session)
    snapshots: list[dict[str, Any]] = []
    total_pnl = 0.0
    total_equity = 0.0
    for project in projects:
        snap = await build_portfolio_snapshot(session, project=project)
        snapshots.append(snap)
        total_pnl += float(snap.get("total_pnl_usd") or 0.0)
        total_equity += float(snap.get("equity_usd") or 0.0)

    return {
        "enabled": settings.paper_trading_enabled,
        "mode": "paper",
        "project_count": len(snapshots),
        "total_equity_usd": round(total_equity, 2),
        "total_pnl_usd": round(total_pnl, 2),
        "projects": snapshots,
        "disclaimer": "Paper trading only — simulated fills, no broker connection.",
    }


async def deposit_paper_cash(
    session: AsyncSession,
    *,
    project: ExternalProject,
    amount_usd: float,
) -> dict[str, Any]:
    """Add simulated capital to a paper trading project ledger."""

    if not _is_paper_project(project):
        msg = "Paper deposit only allowed for paper-mode trading projects."
        raise ValueError(msg)
    if amount_usd <= 0 or amount_usd > 1_000_000:
        msg = "Deposit amount must be between 0 and 1_000_000 USD."
        raise ValueError(msg)

    account = await get_or_create_account(session, project=project)
    account.cash_usd = _d(float(account.cash_usd) + amount_usd)
    logger.info(
        "paper_trading.deposit",
        project_id=str(project.id),
        amount_usd=amount_usd,
        cash_usd=float(account.cash_usd),
    )
    return {
        "project_id": str(project.id),
        "deposited_usd": round(amount_usd, 2),
        "cash_usd": float(account.cash_usd),
        "mode": "paper",
    }


async def reset_paper_account(
    session: AsyncSession,
    *,
    project: ExternalProject,
) -> dict[str, Any]:
    """Reset paper cash to starting balance and clear halt flags (fills retained for audit)."""

    if not _is_paper_project(project):
        msg = "Paper reset only allowed for paper-mode trading projects."
        raise ValueError(msg)

    settings_blob = _project_settings(project)
    starting = float(settings_blob.get("starting_cash_usd") or settings.paper_trading_default_cash_usd)
    account = await get_or_create_account(session, project=project)
    account.cash_usd = _d(starting)
    account.realized_pnl_usd = _d(0)
    account.daily_realized_pnl_usd = _d(0)
    account.is_halted = False
    account.halt_reason = None
    account.daily_pnl_reset_at = datetime.now(tz=UTC)
    return {
        "project_id": str(project.id),
        "cash_usd": starting,
        "mode": "paper",
        "message": "Paper cash reset — fill history kept for stats.",
    }


__all__ = [
    "build_dashboard_paper_summary",
    "build_portfolio_snapshot",
    "deposit_paper_cash",
    "get_or_create_account",
    "list_paper_trading_projects",
    "reset_paper_account",
    "run_paper_trading_tick_all",
    "run_paper_trading_tick_for_project",
]
