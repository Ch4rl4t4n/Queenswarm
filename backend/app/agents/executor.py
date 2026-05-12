"""UniversalAgentExecutor — runs UI-defined bees via LiteLLM + optional tool fan-out."""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
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

from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.models.enums import TaskStatus
from app.models.task import Task

logger = get_logger(__name__)


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
        return "\n".join(lines) or "(no instant results)"
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
        return blob or "(empty body)"
    except Exception as exc:  # noqa: BLE001
        return f"scrape error: {exc}"


async def tool_wikipedia(client: httpx.AsyncClient, topic: str) -> str:
    """Wikipedia REST summary."""

    try:
        slug = topic.replace(" ", "_")
        response = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")
        data = response.json()
        extract = str(data.get("extract", f"No Wikipedia article found for: {topic}"))[:1500]
        return extract
    except Exception as exc:  # noqa: BLE001
        return f"wikipedia error: {exc}"


TOOL_REGISTRY = {
    "web_search": tool_web_search,
    "youtube": tool_youtube,
    "coingecko": tool_coingecko,
    "rss": tool_rss,
    "scrape_url": tool_scrape_url,
    "wikipedia": tool_wikipedia,
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
) -> None:
    """Persist rich output on the backlog row for dashboard polling."""

    task = await session.get(Task, task_id)
    if task is None:
        logger.warning("executor.dashboard_missing_task", task_id=str(task_id))
        return
    task.result = {"output": content, "format": fmt}
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
    tools: list[Any],
    *,
    agent_name: str,
    output_config: dict[str, Any],
) -> dict[str, str]:
    """Execute tool fan-out concurrently."""

    tool_results: dict[str, str] = {}
    if not tools:
        return tool_results

    async with httpx.AsyncClient(timeout=20.0) as client:
        pending: dict[str, Any] = {}
        for spec in tools:
            if isinstance(spec, str):
                name = spec
                extra: dict[str, Any] = {}
            elif isinstance(spec, dict):
                name = str(spec.get("name") or "")
                extra = dict(spec.get("args") or {})
            else:
                continue
            if name not in TOOL_REGISTRY:
                continue
            merged = {**_tool_defaults(name, agent_name, output_config), **extra}
            fn = TOOL_REGISTRY[name]
            if name == "rss":
                pending[name] = fn(**merged)
            else:
                pending[name] = fn(client, **merged)

        if not pending:
            return tool_results

        keys = list(pending.keys())
        results = await asyncio.gather(*pending.values(), return_exceptions=True)
        for key, res in zip(keys, results, strict=True):
            if isinstance(res, Exception):
                tool_results[key] = f"error: {res}"
            else:
                tool_results[key] = str(res)
    return tool_results


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

    logger.info(
        "executor.start",
        agent_name=agent_name,
        task_id=str(task_id),
        tools=tools,
        output_format=output_format,
        output_destination=output_destination,
    )

    tool_results = await run_tool_bundle(tools, agent_name=agent_name, output_config=output_config)
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
    router = LiteLLMRouter()
    try:
        llm_output = await router.decompose(
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
            await deliver_to_dashboard(session, content=llm_output, task_id=task_id, fmt=output_format)
        elif dest.startswith("email"):
            await deliver_to_email(formatted_bytes, output_config, output_format)
            await deliver_to_dashboard(session, content=llm_output, task_id=task_id, fmt=output_format)
        elif dest.startswith("slack"):
            await deliver_to_slack(llm_output, output_config)
            await deliver_to_dashboard(session, content=llm_output, task_id=task_id, fmt=output_format)
        elif dest == "file":
            saved = await deliver_to_file(formatted_bytes, output_config, output_format, agent_name)
            await deliver_to_dashboard(
                session,
                content=f"File saved: {saved}\n\n{llm_output}",
                task_id=task_id,
                fmt=output_format,
            )
        else:
            await deliver_to_dashboard(session, content=llm_output, task_id=task_id, fmt=output_format)
    except Exception as exc:  # noqa: BLE001
        logger.error("executor.delivery_failed", dest=dest, error=str(exc))
        await deliver_to_dashboard(
            session,
            content=f"Delivery error: {exc}\n\nOutput:\n{llm_output}",
            task_id=task_id,
            fmt=output_format,
        )

    preview = llm_output[:500]
    return {
        "agent_id": agent_config.get("agent_id"),
        "task_id": str(task_id),
        "output_format": output_format,
        "output_destination": output_destination,
        "tool_results": {k: v[:200] for k, v in tool_results.items()},
        "output_preview": preview,
        "status": "completed",
    }


async def mark_task_failed(session: AsyncSession, task_id: uuid.UUID, message: str) -> None:
    """Surface hard failures on the backlog row."""

    task_row = await session.get(Task, task_id)
    if task_row is None:
        return
    task_row.status = TaskStatus.FAILED
    task_row.error_msg = message[:4000]
    task_row.completed_at = datetime.now(tz=UTC)
    await session.flush()


__all__ = ["execute_universal_agent", "mark_task_failed"]
