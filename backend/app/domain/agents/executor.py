"""UniversalAgentExecutor — runs UI-defined bees via LiteLLM + optional tool fan-out."""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import time
from datetime import UTC, datetime
import smtplib
import uuid
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import feedparser
import httpx
from html.parser import HTMLParser
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool
from app.application.services.super_tool_router import invoke_mcp_with_router_fallback

from app.core import metrics as hive_metrics
from app.core.config import settings as hive_settings
from app.core.llm_router import LiteLLMRouter
from app.core.database import async_session
from app.core.logging import get_logger
from app.core.notifications import notify_task_complete
from app.infrastructure.persistence.models import load_all_models
from app.infrastructure.persistence.models.enums import TaskStatus, TaskType
from app.infrastructure.persistence.models.task import Task

logger = get_logger(__name__)


def _guard_external_tool_output(blob: str, *, tool: str) -> str:
    """Checkpoint 2/3 — sanitize untrusted web/search tool output before LLM ingest."""

    from app.application.services.prompt_injection_guard import (
        InjectionCheckpoint,
        sanitize_untrusted_text,
    )

    safe, scan = sanitize_untrusted_text(blob, checkpoint=InjectionCheckpoint.EXTERNAL_TOOL)
    if scan.blocked:
        logger.warning(
            "prompt_injection_guard.tool_output_blocked",
            agent_id="executor",
            tool=tool,
            matched_pattern=scan.matched_pattern,
        )
    return safe

load_all_models()


def hive_llm_credentials_ready() -> bool:
    """Return ``True`` when at least one LiteLLM-backed provider secret is configured."""

    from app.application.services.llm_runtime_credentials import (
        provider_effective_anthropic,
        provider_effective_grok,
        provider_effective_openai,
        provider_effective_openrouter,
    )

    return any(
        (
            provider_effective_grok(),
            provider_effective_anthropic(),
            provider_effective_openai(),
            provider_effective_openrouter(),
        ),
    )


def markdown_no_llm_fallback(
    *,
    agent_name: str,
    user_prompt: str,
    tool_results: dict[str, Any],
) -> str:
    """Human-readable report when LiteLLM cannot run (missing keys)."""

    lines: list[str] = [
        f"# {agent_name} — Data Report",
        "*Generated without LLM API keys — deterministic tool payloads only.*",
        "",
        "## Operator Prompt",
        user_prompt.strip() or "(empty)",
        "",
    ]
    if tool_results:
        for tool_name, tool_data in tool_results.items():
            title = tool_name.replace("_", " ").title()
            lines.append(f"## {title}")
            lines.append(str(tool_data)[:4000])
            lines.append("")
    else:
        lines.extend(
            [
                "## Tools",
                "(No tools executed — enable tools if you expected scraped data.)",
                "",
            ]
        )

    bundled = json.dumps(tool_results or {}, indent=2, ensure_ascii=False)[:8000]
    lines.extend(
        [
            "---",
            "### Raw tool JSON",
            "```json",
            bundled,
            "```",
            "",
            "### Full cognition",
            "Set `GROK_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in `.env`, then recreate Celery.",
        ]
    )
    return "\n".join(lines).strip()


def _output_dir() -> Path:
    """Resolve writable directory inside the Docker container."""

    raw = os.getenv("QUEENSWARM_OUTPUT_DIR", "/tmp/queenswarm_outputs")
    return Path(raw)


class _TextExtractor(HTMLParser):
    """Strip scripts/styles and concatenate visible text snippets."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag in ("script", "style", "nav", "footer"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._parts.append(data.strip())


def _tool_defaults(name: str, agent_name: str, oc: dict[str, Any]) -> dict[str, Any]:
    """Merge stored ``output_config`` hints with deterministic fallbacks."""

    if name == "web_search":
        return {"query": str(oc.get("web_search_query") or oc.get("search_query") or agent_name)}
    if name == "youtube":
        return {"query": str(oc.get("youtube_query") or agent_name), "max_results": int(oc.get("youtube_max", 5))}
    if name == "coingecko":
        return {"coin_id": str(oc.get("coingecko_coin_id") or "bitcoin")}
    if name == "rss":
        return {
            "url": str(oc.get("rss_url") or "https://feeds.bbci.co.uk/news/rss.xml"),
            "max_items": int(oc.get("rss_max_items", 5)),
        }
    if name == "scrape_url":
        return {"url": str(oc.get("scrape_url") or "https://example.com")}
    if name == "wikipedia":
        return {"topic": str(oc.get("wikipedia_topic") or agent_name)}
    if name == "grokipedia":
        slug_src = oc.get("grokipedia_slug") or oc.get("topic") or agent_name
        return {"slug": str(slug_src)}
    if name == "serper_search":
        return {"query": str(oc.get("serper_query") or oc.get("search_query") or agent_name)}
    if name == "tavily_search":
        return {"query": str(oc.get("tavily_query") or oc.get("search_query") or agent_name)}
    if name == "jina_reader":
        return {"reader_url": str(oc.get("jina_reader_url") or oc.get("scrape_url") or "")}
    if name == "mcp_invoke":
        return dict(oc.get("mcp_invoke_args") or {})
    return {}


async def tool_web_search(client: httpx.AsyncClient, query: str) -> str:
    """DuckDuckGo lite JSON."""

    try:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": "1", "no_html": "1"},
        )
        data = response.json()
        topics = data.get("RelatedTopics", [])[:5]
        lines: list[str] = []
        for item in topics:
            if isinstance(item, dict) and item.get("Text"):
                lines.append(str(item["Text"]))
        return _guard_external_tool_output("\n".join(lines) or "(no instant results)", tool="web_search")
    except Exception as exc:  # noqa: BLE001
        return f"web_search error: {exc}"


async def tool_youtube(client: httpx.AsyncClient, query: str, max_results: int = 5) -> str:
    """YouTube Data API v3 search when ``YOUTUBE_API_KEY`` is present."""

    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return f"YouTube search skipped (no YOUTUBE_API_KEY). Query was: {query}"
    try:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "order": "date",
                "maxResults": max_results,
                "key": api_key,
            },
        )
        items = response.json().get("items", [])
        lines = []
        for item in items:
            sn = item.get("snippet", {})
            lines.append(
                f"- {sn.get('title')} ({sn.get('channelTitle')}): "
                f"{str(sn.get('description', ''))[:150]}",
            )
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"youtube error: {exc}"


async def tool_coingecko(client: httpx.AsyncClient, coin_id: str) -> str:
    """CoinGecko public price endpoint."""

    try:
        response = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
        )
        block = response.json().get(coin_id, {})
        return json.dumps(block)
    except Exception as exc:  # noqa: BLE001
        return f"coingecko error: {exc}"


async def tool_rss(url: str, max_items: int = 5) -> str:
    """Parse RSS/Atom via feedparser (sync) offloaded to a thread."""

    def _parse() -> str:
        parsed = feedparser.parse(url)
        lines: list[str] = []
        for entry in parsed.entries[:max_items]:
            title = entry.get("title", "")
            summary = str(entry.get("summary", ""))[:150]
            lines.append(f"- {title}: {summary}")
        return "\n".join(lines) or "(empty feed)"

    try:
        return await asyncio.to_thread(_parse)
    except Exception as exc:  # noqa: BLE001
        return f"rss error: {exc}"


async def tool_scrape_url(client: httpx.AsyncClient, url: str) -> str:
    """Naive HTML → text extraction."""

    try:
        response = await client.get(url, follow_redirects=True, timeout=15.0)
        parser = _TextExtractor()
        parser.feed(response.text)
        blob = " ".join(parser._parts)[:2000]  # noqa: SLF001
        return _guard_external_tool_output(blob or "(empty body)", tool="scrape_url")
    except Exception as exc:  # noqa: BLE001
        return f"scrape error: {exc}"


async def tool_wikipedia(client: httpx.AsyncClient, topic: str) -> str:
    """Wikipedia REST summary."""

    try:
        slug = topic.replace(" ", "_")
        response = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")
        data = response.json()
        extract = str(data.get("extract", f"No Wikipedia article found for: {topic}"))[:1500]
        return _guard_external_tool_output(extract, tool="wikipedia")
    except Exception as exc:  # noqa: BLE001
        return f"wikipedia error: {exc}"




async def tool_grokipedia(client: httpx.AsyncClient, slug: str) -> str:
    """Fetch Grokipedia HTML and strip markup (hive research lane prefers this over Wikipedia)."""

    cfg_base = hive_settings.grokipedia_base_url.strip().rstrip('/')
    if not cfg_base:
        return 'grokipedia error: grokipedia_base_url unset'
    path_slug = slug.replace(' ', '_')
    url_txt = f"{cfg_base}/wiki/{path_slug}"
    try:
        response = await client.get(url_txt, follow_redirects=True, timeout=min(12.0, hive_settings.dynamic_connector_tool_timeout_ms / 1000.0))
        parser=_TextExtractor()
        parser.feed(response.text)
        blob = ' '.join(parser._parts)[:2200]
        return _guard_external_tool_output(blob or f'(empty grokipedia body for {slug})', tool="grokipedia")
    except Exception as exc:  # noqa: BLE001
        return f'grokipedia error: {exc}'


async def tool_serper_search(client: httpx.AsyncClient, query: str, *, api_key: str | None = None) -> str:
    """Serper.dev Google-lite JSON snippets when ``SERPER_API_KEY`` provisions."""

    key = (api_key or os.getenv('SERPER_API_KEY', '')).strip()
    if not key:
        return 'serper_search skipped — export SERPER_API_KEY for paid JSON search.'
    try:
        response = await client.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
            json={'q': query, 'num': 5},
            timeout=min(15.0, hive_settings.dynamic_connector_tool_timeout_ms / 1000.0),
        )
        data=response.json()
        organic=data.get('organic') or []
        lines:list[str]=[]
        for hit in organic[:5]:
            if isinstance(hit, dict):
                title=str(hit.get('title',''))
                link=str(hit.get('link',''))
                snippet=str(hit.get('snippet',''))[:200]
                lines.append(f'- {title} :: {snippet} ({link})')
        return _guard_external_tool_output('\n'.join(lines) or '(serper empty)', tool="serper_search")
    except Exception as exc:  # noqa: BLE001
        return f'serper error: {exc}'


async def tool_tavily_search(client: httpx.AsyncClient, query: str, *, api_key: str | None = None) -> str:
    """Tavily answer-style search when ``TAVILY_API_KEY`` is present."""

    key = (api_key or os.getenv('TAVILY_API_KEY', '')).strip()
    if not key:
        return 'tavily_search skipped — export TAVILY_API_KEY.'
    try:
        response = await client.post(
            'https://api.tavily.com/search',
            json={'api_key': key, 'query': query, 'search_depth':'basic'},
            timeout=min(15.0,hive_settings.dynamic_connector_tool_timeout_ms / 1000.0),
        )
        blob=response.json()
        results=blob.get('results') if isinstance(blob, dict) else None
        lines:list[str]=[]
        if isinstance(results, list):
            for row in results[:5]:
                if isinstance(row, dict):
                    lines.append(str(row.get('content') or row.get('url') or row))
        return _guard_external_tool_output('\n'.join(lines)[:2500] or '(tavily empty)', tool="tavily_search")
    except Exception as exc:  # noqa: BLE001
        return f'tavily error: {exc}'


async def tool_jina_reader(client: httpx.AsyncClient, reader_url: str) -> str:
    """Readable proxy via ``r.jina.ai`` honoring optional ``JINA_API_KEY`` quota."""

    if not reader_url.strip():
        return 'jina_reader skipped — configure reader URL'
    key=os.getenv('JINA_API_KEY','').strip()
    headers=dict[str,str]()
    if key:
        headers['Authorization']=f'Bearer {key}'
    assembled=f'https://r.jina.ai/{reader_url.strip()}'
    try:
        response = await client.get(assembled, headers=headers, timeout=min(20.0, hive_settings.dynamic_connector_tool_timeout_ms / 1000.0))
        return _guard_external_tool_output(response.text[:4000], tool="jina_reader")
    except Exception as exc:  # noqa: BLE001
        return f'jina_reader error: {exc}'


async def tool_mcp_invoke(
    _: httpx.AsyncClient,
    *,
    session: AsyncSession | None,
    connector_slug: str,
    tool_name: str,
    arguments: dict[str, Any],
    connector_allow_tokens: frozenset[str],
    manager_slug: str,
    agent_task_id: str,
    tenant_id: uuid.UUID | None = None,
    router_invoke_plan: dict[str, Any] | None = None,
) -> str:
    """Dynamic Postgres MCP manifests executed with vault-sealed outbound auth."""

    if session is None:
        return "mcp_invoke skipped — missing async DB session."
    lowered = connector_slug.strip().lower()
    routing_mode = str((router_invoke_plan or {}).get("routing_mode") or "").strip().lower()
    if connector_allow_tokens and lowered not in connector_allow_tokens:
        result = f"mcp_invoke blocked for `{connector_slug}` (not manager-allowlisted)."
    elif routing_mode in {"priority", "research_then_action", "parallel_hint"}:
        from app.infrastructure.persistence.models.tenant import Tenant

        tenant_row = await session.get(Tenant, tenant_id) if tenant_id is not None else None
        result = await invoke_mcp_with_router_fallback(
            session,
            tenant=tenant_row,
            manager_slug=manager_slug,
            connector_slug=lowered,
            tool_name=tool_name,
            arguments=dict(arguments),
            agent_task_id=agent_task_id,
        )
    else:
        result = await invoke_dynamic_tool(
            session,
            connector_slug=lowered,
            tool_name=tool_name,
            arguments=dict(arguments),
            manager_slug=None if manager_slug.strip() == "" else manager_slug,
            agent_task_id=agent_task_id,
        )

    if tenant_id is not None:
        from app.application.services.tool_gap_signal import record_tool_gap

        await record_tool_gap(
            tenant_id=tenant_id,
            connector_slug=lowered,
            tool_name=tool_name,
            manager_slug=manager_slug,
            result=result,
        )
    return result



def prioritize_research_connector_tools(
    bundle: list[Any],
    *,
    manager_slug: str,
    allowlist_tokens: frozenset[str],
    agent_name: str,
    oc: dict[str, Any],
) -> list[Any]:
    """Reorder tool specs so Grokipedia + premium search adapters lead Wikipedia in Research lanes."""

    if manager_slug != "research_intelligence":
        return list(bundle)

    normalized: list[dict[str, Any]] = []
    for raw in bundle:
        if isinstance(raw, str):
            cleaned = raw.strip()
            if cleaned:
                normalized.append({"name": cleaned, "args": {}})
        elif isinstance(raw, dict):
            name_txt = str(raw.get("name") or "").strip()
            if name_txt:
                normalized.append({"name": name_txt, "args": dict(raw.get("args") or {})})

    existing_lower = {str(entry["name"]).lower() for entry in normalized}

    slug_val = str(_tool_defaults("grokipedia", agent_name, oc).get("slug") or agent_name)
    query_val = str(_tool_defaults("serper_search", agent_name, oc).get("query") or agent_name)
    jr_url = str(oc.get("jina_reader_url") or "").strip()

    allow_all = len(allowlist_tokens) == 0

    priority_front: list[dict[str, Any]] = []

    if (allow_all or "grokipedia" in allowlist_tokens) and "grokipedia" not in existing_lower:
        priority_front.append({"name": "grokipedia", "args": {"slug": slug_val}})

    if "serper_search" not in existing_lower:
        priority_front.append({"name": "serper_search", "args": {"query": query_val}})

    if "tavily_search" not in existing_lower:
        priority_front.append({"name": "tavily_search", "args": {"query": query_val}})

    if jr_url and "jina_reader" not in existing_lower:
        priority_front.append({"name": "jina_reader", "args": {"reader_url": jr_url}})

    wiki_items = [row for row in normalized if str(row["name"]).lower() == "wikipedia"]
    mid_items = [row for row in normalized if str(row["name"]).lower() != "wikipedia"]

    dedup_seen: set[str] = set()
    ordered_mid: list[dict[str, Any]] = []

    def _remember(row: dict[str, Any]) -> None:
        dedup_seen.add(str(row["name"]).lower())

    for chunk in [*priority_front, *mid_items]:
        key = str(chunk["name"]).lower()
        if key in dedup_seen:
            continue
        ordered_mid.append(chunk)
        _remember(chunk)

    for wiki_row in wiki_items:
        ordered_mid.append(wiki_row)

    return ordered_mid




TOOL_REGISTRY = {
    "web_search": tool_web_search,
    "youtube": tool_youtube,
    "coingecko": tool_coingecko,
    "rss": tool_rss,
    "scrape_url": tool_scrape_url,
    "wikipedia": tool_wikipedia,
    "grokipedia": tool_grokipedia,
    "serper_search": tool_serper_search,
    "tavily_search": tool_tavily_search,
    "jina_reader": tool_jina_reader,
    "mcp_invoke": tool_mcp_invoke,
}


def format_as_text(content: str) -> bytes:
    """Encode plain utf-8."""

    return content.encode("utf-8")


def format_as_markdown(content: str) -> bytes:
    """Markdown share the same on-wire representation as text."""

    return content.encode("utf-8")


def format_as_json_bytes(content: str) -> bytes:
    """Normalize JSON-ish model output."""

    stripped = content.strip()
    try:
        if stripped.startswith("{"):
            obj = json.loads(stripped)
        elif stripped.startswith("["):
            obj = json.loads(stripped)
        else:
            obj = {"output": content}
        return json.dumps(obj, indent=2).encode("utf-8")
    except json.JSONDecodeError:
        return json.dumps({"output": content}).encode("utf-8")


def format_as_excel(content: str) -> bytes:
    """Best-effort spreadsheet export."""

    try:
        import openpyxl  # type: ignore[import-not-found]

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        try:
            data = json.loads(content)
            if isinstance(data, list) and data:
                headers = list(data[0].keys())
                sheet.append(headers)
                for row in data:
                    sheet.append([str(row.get(h, "")) for h in headers])
            elif isinstance(data, dict):
                for key, value in data.items():
                    sheet.append([key, str(value)])
        except json.JSONDecodeError:
            for line in content.strip().split("\n"):
                sheet.append(line.split(","))

        buf = io.BytesIO()
        workbook.save(buf)
        return buf.getvalue()
    except ImportError:
        logger.warning("executor.openpyxl_missing_falling_back_csv")
        return format_as_csv(content)


def format_as_csv(content: str) -> bytes:
    """Serialize list[dict] or raw text as CSV bytes."""

    try:
        data = json.loads(content)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            import csv

            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)  # type: ignore[arg-type]
            return buffer.getvalue().encode("utf-8")
    except Exception:  # noqa: BLE001
        pass
    return content.encode("utf-8")


def format_as_html(content: str) -> bytes:
    """Wrap arbitrary HTML fragment."""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body{{font-family:sans-serif;max-width:900px;margin:auto;padding:2rem;}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}</style>
</head><body>{content}</body></html>"""
    return html.encode("utf-8")


OUTPUT_FORMATTERS: dict[str, Any] = {
    "text": format_as_text,
    "markdown": format_as_markdown,
    "json": format_as_json_bytes,
    "excel": format_as_excel,
    "csv": format_as_csv,
    "html": format_as_html,
}


async def deliver_to_dashboard(
    session: AsyncSession,
    *,
    content: str,
    task_id: uuid.UUID,
    fmt: str,
    cost_usd: float | None = None,
) -> None:
    """Persist rich output on the backlog row for dashboard polling."""

    task = await session.get(Task, task_id)
    if task is None:
        logger.warning("executor.dashboard_missing_task", task_id=str(task_id))
        return
    payload: dict[str, Any] = {"output": content, "format": fmt}
    if cost_usd is not None and cost_usd > 0:
        payload["cost_usd"] = round(float(cost_usd), 8)
    task.result = payload
    task.status = TaskStatus.COMPLETED
    task.error_msg = None
    task.completed_at = datetime.now(tz=UTC)


async def deliver_to_email(content: bytes, config: dict[str, Any], fmt: str) -> None:
    """SMTP delivery using operator-provided env credentials."""

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    to_email = str(config.get("email_to") or smtp_user)
    subject = str(config.get("email_subject") or "Queenswarm Agent Report")

    if not smtp_user:
        logger.warning("executor.email_skipped_no_smtp_user")
        return

    def _send() -> None:
        message = MIMEMultipart()
        message["From"] = smtp_user
        message["To"] = to_email
        message["Subject"] = subject

        if fmt in ("text", "markdown", "json"):
            message.attach(MIMEText(content.decode("utf-8", errors="replace"), "plain"))
        else:
            ext = {"excel": "xlsx", "csv": "csv", "html": "html"}.get(fmt, "txt")
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="report.{ext}"')
            message.attach(part)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(message)

    await asyncio.to_thread(_send)
    logger.info("executor.email_sent", to=to_email)


async def deliver_to_slack(content: str, config: dict[str, Any]) -> None:
    """Incoming webhook post."""

    webhook = str(config.get("slack_webhook") or os.getenv("SLACK_WEBHOOK_URL", ""))
    if not webhook:
        logger.warning("executor.slack_skipped_no_webhook")
        return
    channel = str(config.get("slack_channel", "#queenswarm"))
    payload = {
        "channel": channel,
        "text": f"🐝 *Queenswarm Agent Report*\n```{content[:2900]}```",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(webhook, json=payload)
    logger.info("executor.slack_posted", channel=channel)


async def deliver_to_file(content: bytes, config: dict[str, Any], fmt: str, agent_name: str) -> str:
    """Persist binary exports for operators (tmpfs by default)."""

    target_dir = _output_dir()
    await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
    ext = {"excel": "xlsx", "csv": "csv", "html": "html", "json": "json", "markdown": "md"}.get(fmt, "txt")
    template = str(config.get("filename_template") or f"{agent_name}_{{date}}.{ext}")
    filename = template.replace("{date}", datetime.now(tz=UTC).strftime("%Y%m%d_%H%M"))
    path = target_dir / filename

    def _write() -> None:
        path.write_bytes(content)

    await asyncio.to_thread(_write)
    logger.info("executor.file_saved", path=str(path))
    return str(path)






async def run_tool_bundle(
    session: AsyncSession | None,
    tools: list[Any],
    *,
    agent_name: str,
    output_config: dict[str, Any],
    executor_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Execute MCP + classic tools concurrently with connector allowlisting."""

    results: dict[str, str] = {}
    if not tools:
        return results

    ctx_payload = dict(executor_context or {})
    allow_tokens = frozenset(
        str(tok).strip().lower() for tok in (ctx_payload.get("connector_allowlist") or []) if str(tok).strip()
    )
    manager_lane = str(ctx_payload.get("manager_slug") or "").strip().lower()
    agent_trace = str(ctx_payload.get("task_id") or "executor")
    tenant_id_raw = ctx_payload.get("tenant_id")
    tenant_uuid: uuid.UUID | None = None
    if tenant_id_raw is not None:
        try:
            tenant_uuid = tenant_id_raw if isinstance(tenant_id_raw, uuid.UUID) else uuid.UUID(str(tenant_id_raw))
        except ValueError:
            tenant_uuid = None
    router_invoke_plan = ctx_payload.get("router_invoke_plan")
    router_plan_dict = dict(router_invoke_plan) if isinstance(router_invoke_plan, dict) else None
    research_keys_raw = ctx_payload.get("research_keys")
    research_keys = dict(research_keys_raw) if isinstance(research_keys_raw, dict) else {}

    async with httpx.AsyncClient(timeout=20.0) as client:
        pending: dict[str, Any] = {}
        for raw_spec in tools:
            extra_kwargs: dict[str, Any]
            if isinstance(raw_spec, str):
                label_name = raw_spec.strip()
                extra_kwargs = {}
            elif isinstance(raw_spec, dict):
                label_name = str(raw_spec.get("name") or "").strip()
                extra_kwargs = dict(raw_spec.get("args") or {})
            else:
                continue
            if not label_name:
                continue

            merged_kwargs = {**_tool_defaults(label_name, agent_name, output_config), **extra_kwargs}
            tool_fn = TOOL_REGISTRY.get(label_name)
            if tool_fn is None:
                continue

            unique_tag = uuid.uuid4().hex[:8]

            if label_name == "rss":
                pending[f"{label_name}:{unique_tag}"] = tool_fn(**merged_kwargs)
                continue

            if label_name == "mcp_invoke":
                if session is None:
                    continue
                call_payload = dict(merged_kwargs)
                slug_connector = str(call_payload.pop("connector_slug", "")).strip()
                tool_pick = str(call_payload.pop("tool_name", "invoke")).strip() or "invoke"
                explicit_args = call_payload.pop("arguments", None)
                arg_body = dict(explicit_args) if isinstance(explicit_args, dict) else dict(call_payload)
                if not slug_connector:
                    continue
                if allow_tokens and slug_connector.lower() not in allow_tokens:
                    continue

                pending[f"mcp_invoke:{slug_connector}:{tool_pick}:{unique_tag}"] = tool_fn(
                    client,
                    session=session,
                    connector_slug=slug_connector,
                    tool_name=tool_pick,
                    arguments=arg_body,
                    connector_allow_tokens=allow_tokens,
                    manager_slug=manager_lane,
                    agent_task_id=agent_trace,
                    tenant_id=tenant_uuid,
                    router_invoke_plan=router_plan_dict,
                )
                continue

            if label_name == "tavily_search":
                vault_key = research_keys.get("tavily")
                if isinstance(vault_key, str) and vault_key.strip():
                    merged_kwargs["api_key"] = vault_key.strip()
            elif label_name == "serper_search":
                vault_key = research_keys.get("serper")
                if isinstance(vault_key, str) and vault_key.strip():
                    merged_kwargs["api_key"] = vault_key.strip()

            pending[f"{label_name}:{unique_tag}"] = tool_fn(client, **merged_kwargs)

        if not pending:
            return results

        keys = list(pending.keys())
        gathered = await asyncio.gather(*pending.values(), return_exceptions=True)
        for key_name, outcome in zip(keys, gathered, strict=True):
            if isinstance(outcome, Exception):
                results[key_name] = f"error: {outcome}"
            else:
                results[key_name] = str(outcome)

    return results



async def execute_universal_agent(
    session: AsyncSession,
    *,
    agent_config: dict[str, Any],
    task_id: uuid.UUID,
) -> dict[str, Any]:
    """Run tools → LiteLLM → formatters → delivery surfaces."""

    system_prompt = str(agent_config.get("system_prompt") or "You are a helpful AI agent.")
    tools = agent_config.get("tools") or []
    output_format = str(agent_config.get("output_format") or "text").lower()
    output_destination = str(agent_config.get("output_destination") or "dashboard").lower()
    output_config = dict(agent_config.get("output_config") or {})
    agent_name = str(agent_config.get("name") or "agent")
    user_prompt = str(agent_config.get("user_prompt_template") or "Execute your task now.")

    task_row = await session.get(Task, task_id)
    if task_row is None:
        msg = f"Unknown task_id={task_id}"
        raise ValueError(msg)
    task_row.status = TaskStatus.RUNNING
    task_row.started_at = datetime.now(tz=UTC)
    await session.flush()
    exec_started = time.perf_counter()

    logger.info(
        "executor.start",
        agent_name=agent_name,
        task_id=str(task_id),
        tools=tools,
        output_format=output_format,
        output_destination=output_destination,
    )

    allow_tokens=[
        str(token).strip().lower()
        for token in (agent_config.get("manager_connector_allowlist") or [])
        if str(token).strip()
    ]

    prioritized = prioritize_research_connector_tools(
        tools,
        manager_slug=str(agent_config.get("manager_template_slug") or "").strip().lower(),
        allowlist_tokens=frozenset(allow_tokens),
        agent_name=agent_name,
        oc=output_config,
    )

    hydrated: list[Any] = list(prioritized)

    executor_native = frozenset(k for k in TOOL_REGISTRY if k != "mcp_invoke")

    hydrated_mcp_seen: set[str] = set()
    for cand in hydrated:
        if isinstance(cand, dict) and str(cand.get("name") or "") == "mcp_invoke":
            cs = str((cand.get("args") or {}).get("connector_slug") or "").strip().lower()
            if cs:
                hydrated_mcp_seen.add(cs)

    for slug_token in sorted({tok for tok in allow_tokens if tok not in executor_native}):
        if slug_token in hydrated_mcp_seen:
            continue
        default_tool = "article_fetch" if slug_token == "grokipedia" else "invoke"
        hydrated.append(
            {
                "name": "mcp_invoke",
                "args": {
                    "connector_slug": slug_token,
                    "tool_name": default_tool,
                    "arguments": {},
                },
            }
        )

    executor_payload={
        'connector_allowlist': allow_tokens,
        'manager_slug': str(agent_config.get('manager_template_slug') or ''),
        'task_id': str(task_id),
    }

    manager_lane_slug = str(agent_config.get("manager_template_slug") or "").strip().lower()
    try:
        from app.application.services.super_tool_router import resolve_router_invoke_plan
        from app.core.tenant_context import get_current_tenant_uuid
        from app.infrastructure.persistence.models.tenant import Tenant

        tenant_uuid = get_current_tenant_uuid()
        if tenant_uuid is not None:
            executor_payload["tenant_id"] = str(tenant_uuid)
            tenant_row = await session.get(Tenant, tenant_uuid)
            router_plan = resolve_router_invoke_plan(tenant_row, manager_slug=manager_lane_slug)
            if router_plan is not None:
                executor_payload["router_invoke_plan"] = {
                    "routing_mode": router_plan.routing_mode,
                    "connector_slugs": list(router_plan.connector_slugs),
                    "fallback_builtin_search": router_plan.fallback_builtin_search,
                    "router_slugs": list(router_plan.router_slugs),
                    "max_cost_tier": router_plan.max_cost_tier,
                }
    except ImportError:
        pass

    try:
        from app.application.services.research_runtime_credentials import resolve_research_keys

        executor_payload["research_keys"] = await resolve_research_keys(session)
    except ImportError:
        pass

    tool_results = await run_tool_bundle(
        session,
        hydrated,
        agent_name=agent_name,
        output_config=output_config,
        executor_context=executor_payload,
    )
    tool_context = ""
    if tool_results:
        tool_context = "\n\n## Tool Results\n" + "\n".join(f"### {k}\n{v}" for k, v in tool_results.items())

    format_instructions = {
        "text": "Respond with plain text.",
        "markdown": "Respond with well-formatted Markdown.",
        "json": "Respond with ONLY valid JSON. No explanation, no code fences.",
        "excel": "Respond with a JSON array of objects suitable for spreadsheet rows.",
        "csv": "Respond with CSV data including a header row.",
        "html": "Respond with an HTML fragment (no html/body wrapper).",
    }

    full_user_prompt = f"""{user_prompt}

{tool_context}

## Output Format
{format_instructions.get(output_format, "Respond with plain text.")}"""

    llm_output = ""
    llm_cost_usd: float | None = None
    if not hive_llm_credentials_ready():
        logger.warning(
            "executor.llm_skipped_no_provider_keys",
            agent_name=agent_name,
            task_id=str(task_id),
        )
        llm_output = markdown_no_llm_fallback(
            agent_name=agent_name,
            user_prompt=user_prompt,
            tool_results=tool_results,
        ).strip()
        if output_format == "json":
            llm_output = json.dumps({"summary": llm_output, "tools": tool_results}, indent=2)
    else:
        router = LiteLLMRouter()
        try:
            llm_output, llm_cost_usd = await router.decompose(
                session,
                system_prompt=system_prompt,
                user_payload=full_user_prompt,
                swarm_id=str(agent_config.get("agent_id") or ""),
                task_id=str(task_id),
            )
            llm_output = (llm_output or "").strip()
            if output_format == "json":
                llm_output = re.sub(r"```json|```", "", llm_output, flags=re.IGNORECASE).strip()
        except Exception as exc:  # noqa: BLE001
            logger.error("executor.llm_failed", error=str(exc), task_id=str(task_id))
            llm_output = f"LLM error: {exc}\n\nTool results:\n{json.dumps(tool_results, indent=2)}"

    formatter = OUTPUT_FORMATTERS.get(output_format, format_as_text)
    try:
        formatted_bytes = formatter(llm_output)
    except Exception as exc:  # noqa: BLE001
        logger.warning("executor.format_failed", error=str(exc), fmt=output_format)
        formatted_bytes = llm_output.encode("utf-8")

    dest = output_destination
    try:
        if dest == "dashboard" or dest.startswith("dashboard"):
            await deliver_to_dashboard(
                session,
                content=llm_output,
                task_id=task_id,
                fmt=output_format,
                cost_usd=llm_cost_usd,
            )
        elif dest.startswith("email"):
            await deliver_to_email(formatted_bytes, output_config, output_format)
            await deliver_to_dashboard(
                session,
                content=llm_output,
                task_id=task_id,
                fmt=output_format,
                cost_usd=llm_cost_usd,
            )
        elif dest.startswith("slack"):
            await deliver_to_slack(llm_output, output_config)
            await deliver_to_dashboard(
                session,
                content=llm_output,
                task_id=task_id,
                fmt=output_format,
                cost_usd=llm_cost_usd,
            )
        elif dest == "file":
            saved = await deliver_to_file(formatted_bytes, output_config, output_format, agent_name)
            await deliver_to_dashboard(
                session,
                content=f"File saved: {saved}\n\n{llm_output}",
                task_id=task_id,
                fmt=output_format,
                cost_usd=llm_cost_usd,
            )
        else:
            await deliver_to_dashboard(
                session,
                content=llm_output,
                task_id=task_id,
                fmt=output_format,
                cost_usd=llm_cost_usd,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("executor.delivery_failed", dest=dest, error=str(exc))
        await deliver_to_dashboard(
            session,
            content=f"Delivery error: {exc}\n\nOutput:\n{llm_output}",
            task_id=task_id,
            fmt=output_format,
            cost_usd=llm_cost_usd,
        )

    preview = llm_output[:500]
    task_kind = (
        task_row.task_type.value if isinstance(task_row.task_type, TaskType) else str(task_row.task_type)
    )
    elapsed_exec = max(time.perf_counter() - exec_started, 1e-6)
    hive_metrics.TASKS_TOTAL.labels(task_type=task_kind, status="completed").inc()
    hive_metrics.TASK_DURATION.labels(task_type=task_kind).observe(elapsed_exec)

    try:
        await notify_task_complete(
            agent_name=agent_name,
            task_title=task_row.title or "task",
            output_preview=llm_output,
            cost_usd=float(llm_cost_usd or 0.0),
        )
    except Exception:  # noqa: BLE001 — notifications never block hive execution
        pass

    return {
        "agent_id": agent_config.get("agent_id"),
        "task_id": str(task_id),
        "output_format": output_format,
        "output_destination": output_destination,
        "tool_results": {k: v[:200] for k, v in tool_results.items()},
        "output_preview": preview,
        "status": "completed",
    }


async def execute_agent(agent_config: dict[str, Any], run_label: str) -> dict[str, Any]:
    """Persist an ``agent_run`` task row then run :func:`execute_universal_agent`.

    Args:
        agent_config: Keys accepted by ``execute_universal_agent`` (UUID ``agent_id`` may be text).
        run_label: Human-readable slug stored in Task.title for tracing.

    Returns:
        Executor result dict mirroring universal agent delivery.
    """

    raw_agent = agent_config.get("agent_id")
    agent_uuid: uuid.UUID | None = None
    if raw_agent is not None:
        agent_uuid = uuid.UUID(str(raw_agent)) if not isinstance(raw_agent, uuid.UUID) else raw_agent

    async with async_session() as session:
        task_row = Task(
            title=f"run:{run_label}",
            task_type=TaskType.AGENT_RUN,
            status=TaskStatus.PENDING,
            agent_id=agent_uuid,
            payload={"runner": "execute_agent", "label": run_label},
        )
        session.add(task_row)
        await session.flush()

        return await execute_universal_agent(
            session,
            agent_config=agent_config,
            task_id=task_row.id,
        )


async def mark_task_failed(session: AsyncSession, task_id: uuid.UUID, message: str) -> None:
    """Surface hard failures on the backlog row."""

    task_row = await session.get(Task, task_id)
    if task_row is None:
        return
    task_kind = (
        task_row.task_type.value if isinstance(task_row.task_type, TaskType) else str(task_row.task_type)
    )
    hive_metrics.TASKS_TOTAL.labels(task_type=task_kind, status="failed").inc()
    task_row.status = TaskStatus.FAILED
    task_row.error_msg = message[:4000]
    task_row.completed_at = datetime.now(tz=UTC)
    await session.flush()


__all__ = [
    "execute_agent",
    "execute_universal_agent",
    "hive_llm_credentials_ready",
    "markdown_no_llm_fallback",
    "mark_task_failed",
]
