"""Shared analytics deliverable helpers — avoids circular imports between DA5/DA6."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

ANALYTICS_REPORT_FORMAT = "queenswarm.analytics_report.v1"
ANALYTICS_ARTIFACT_TAGS = frozenset({"analytics", "decision-report", "business-question"})

ChartType = Literal["bar", "line", "kpi"]


class AnalyticsChartBlockOut(BaseModel):
    """One chart or KPI block bound to report artifact structured JSON."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    chart_type: ChartType
    title: str = Field(min_length=1, max_length=200)
    labels: list[str] = Field(default_factory=list, max_length=24)
    values: list[float] = Field(default_factory=list, max_length=24)
    unit: str = Field(default="", max_length=32)
    source_citation: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _validate_chart_shape(self) -> AnalyticsChartBlockOut:
        if self.chart_type == "kpi" and len(self.values) < 1:
            msg = "KPI chart blocks require at least one value."
            raise ValueError(msg)
        if self.chart_type in {"bar", "line"}:
            if len(self.values) < 1:
                msg = "Bar and line chart blocks require values."
                raise ValueError(msg)
            if self.labels and len(self.labels) != len(self.values):
                msg = "Labels and values length must match for bar/line charts."
                raise ValueError(msg)
        return self


def is_analytics_deliverable(row: TaskFinalDeliverable) -> bool:
    """True when deliverable belongs to analytics workspace lane."""

    tags = {str(t).strip().lower() for t in row.tags if isinstance(row.tags, list)}
    if tags & ANALYTICS_ARTIFACT_TAGS:
        return True
    structured = row.structured_json if isinstance(row.structured_json, dict) else {}
    fmt = str(structured.get("format") or "")
    return fmt.startswith("queenswarm.analytics")


def parse_chart_blocks(structured: dict[str, Any]) -> list[AnalyticsChartBlockOut]:
    """Parse chart blocks array from deliverable structured JSON."""

    raw = structured.get("chart_blocks")
    if not isinstance(raw, list):
        return []
    blocks: list[AnalyticsChartBlockOut] = []
    for idx, item in enumerate(raw[:12]):
        if not isinstance(item, dict):
            continue
        try:
            blocks.append(
                AnalyticsChartBlockOut(
                    id=str(item.get("id") or f"chart-{idx + 1}"),
                    chart_type=item.get("chart_type") or item.get("type") or "kpi",
                    title=str(item.get("title") or "Metric"),
                    labels=[str(x) for x in item.get("labels", [])][:24],
                    values=[float(x) for x in item.get("values", [])][:24],
                    unit=str(item.get("unit") or ""),
                    source_citation=str(item.get("source_citation") or ""),
                ),
            )
        except (TypeError, ValueError):
            continue
    return blocks


__all__ = [
    "ANALYTICS_ARTIFACT_TAGS",
    "ANALYTICS_REPORT_FORMAT",
    "AnalyticsChartBlockOut",
    "ChartType",
    "is_analytics_deliverable",
    "parse_chart_blocks",
]
