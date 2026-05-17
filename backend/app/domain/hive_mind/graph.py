"""Neo4j writers + capped graph snapshots for Hive Mind constellation."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.neo4j_client import get_neo4j_driver


async def persist_hive_graph_bundle(
    *,
    deliverable_id: uuid.UUID,
    lineage_id: uuid.UUID,
    version: int,
    title: str,
    slug: str,
    summary: str,
    tags: list[str],
    dashboard_user_id_str: str,
    reflection_excerpt: str,
    insight_summary: str,
    insight_body: str,
    mission_id: uuid.UUID | None,
    manager_slugs: list[str],
    source_task_id: uuid.UUID | None,
    markdown_excerpt: str,
) -> None:
    """Upsert `:Deliverable` constellation with bounded fan-out correlations."""
    driver = await get_neo4j_driver()
    did = str(deliverable_id)
    lid = str(lineage_id)
    mids = sorted({slug.strip().lower().replace(" ", "_") for slug in manager_slugs if slug.strip()})
    refl_body = reflection_excerpt[:8000].strip()
    ins_body = insight_body[:4800].strip()
    dash_uid = (dashboard_user_id_str or "").strip()

    merge_deliverable = """
    MERGE (d:Deliverable {deliverable_id: $did})
    SET d.lineage_id = $lid,
        d.version = $version,
        d.title = $title,
        d.slug = $slug,
        d.summary = $summary,
        d.tags = $tags,
        d.dashboard_user_id = $dash_uid,
        d.markdown_excerpt = $exc,
        d.updated_at = datetime()
    """
    async with driver.session(database="neo4j") as session:
        await session.run(
            merge_deliverable,
            did=did,
            lid=lid,
            version=int(version),
            title=title[:500],
            slug=slug[:200],
            summary=summary[:2000],
            tags=tags[:32],
            dash_uid=dash_uid[:120],
            exc=markdown_excerpt[:2600],
        )

        if mission_id:
            await session.run(
                """
                MERGE (t:Task {task_id: $tid})
                SET t.kind = 'ballroom_mission',
                    t.updated_at = datetime()
                WITH t
                MATCH (d:Deliverable {deliverable_id: $did})
                MERGE (d)-[:FULFILLED_FOR]->(t)
                """,
                tid=str(mission_id),
                did=did,
            )

        for slug_txt in mids:
            await session.run(
                """
                MERGE (m:ManagerTemplate {slug: $slug})
                SET m.updated_at = datetime()
                WITH m
                MATCH (d:Deliverable {deliverable_id: $did})
                MERGE (d)-[:USED_MANAGER_TEMPLATE]->(m)
                """,
                slug=slug_txt,
                did=did,
            )

        if refl_body:
            await session.run(
                """
                MERGE (r:Reflection {origin_deliverable: $did, version: $version})
                SET r.body_excerpt = $body,
                    r.updated_at = datetime()
                WITH r
                MATCH (d:Deliverable {deliverable_id: $did})
                MERGE (d)-[:HAS_REFLECTION]->(r)
                """,
                body=refl_body,
                version=int(version),
                did=did,
            )

        if ins_body or insight_summary.strip():
            await session.run(
                """
                MERGE (ins:Insight {origin_deliverable: $did, version: $version})
                SET ins.summary = $summary,
                    ins.body = $body,
                    ins.deliverable_version = $version,
                    ins.updated_at = datetime()
                WITH ins
                MATCH (d:Deliverable {deliverable_id: $did})
                MERGE (d)-[:HAS_INSIGHT]->(ins)
                """,
                summary=insight_summary[:400],
                body=ins_body,
                version=int(version),
                did=did,
            )

        for tag in tags[:16]:
            tag_norm = tag.strip().lower().replace(" ", "_")
            if len(tag_norm) < 2:
                continue
            await session.run(
                """
                MERGE (tg:Tag {name: $name})
                SET tg.updated_at = datetime()
                WITH tg
                MATCH (d:Deliverable {deliverable_id: $did})
                MERGE (d)-[:TAGGED_AS]->(tg)
                """,
                name=tag_norm[:160],
                did=did,
            )

        if source_task_id:
            await session.run(
                """
                MERGE (tk:Task {task_id: $stid})
                SET tk.kind = 'hive_task_reference',
                    tk.updated_at = datetime()
                WITH tk
                MATCH (d:Deliverable {deliverable_id: $did})
                MERGE (d)-[:SOURCED_FROM_TASK]->(tk)
                """,
                stid=str(source_task_id),
                did=did,
            )

        if int(version) > 1:
            await session.run(
                """
                MATCH (curr:Deliverable {deliverable_id: $did})
                MATCH (prev:Deliverable {lineage_id: $lid})
                WHERE prev.deliverable_id <> $did AND prev.version = $prev_ver
                MERGE (curr)-[:SUPERSEDES]->(prev)
                """,
                did=did,
                lid=lid,
                prev_ver=int(version) - 1,
            )

        await session.run(
            """
            MATCH (a:Deliverable {deliverable_id: $did})
            MATCH (b:Deliverable)
            WHERE a.deliverable_id <> b.deliverable_id
              AND size([t IN coalesce(a.tags, []) WHERE t IN coalesce(b.tags, []) AND t <> '']) > 0
            WITH b ORDER BY b.updated_at DESC LIMIT 12
            MATCH (base:Deliverable {deliverable_id: $did})
            MERGE (base)-[:CORRELATES_WITH {basis: 'shared_tag'}]->(b)
            """,
            did=did,
        )


def _pick_label(kind: str, props: dict[str, Any]) -> str:
    """Derive explorer label from heterogeneous node payloads."""

    if kind == "Deliverable":
        return str(props.get("title") or props.get("slug") or props.get("deliverable_id"))[:180]
    if kind == "Tag":
        return f"#{props.get('name', 'tag')}"
    if kind == "Insight":
        return str(props.get("summary") or "Insight")[:180]
    if kind == "Reflection":
        excerpt = props.get("body_excerpt") or ""
        excerpt_s = excerpt[:140] + ("…" if len(str(excerpt)) > 140 else "")
        return f"Reflection {excerpt_s}"
    if kind == "ManagerTemplate":
        return str(props.get("slug") or "manager")[:140]
    if kind == "Task":
        tid = props.get("task_id") or "task"
        return f"Task {tid}"[:140]
    return kind


async def bounded_operator_graph_snapshot(
    *,
    dashboard_user_id: str,
    limit_nodes: int,
) -> dict[str, Any]:
    """Deliver limited neighbourhood rows for dashboards (Neo4j only — cheap hop cap)."""

    driver = await get_neo4j_driver()
    lim = max(4, min(int(limit_nodes), 200))
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    stmt = """
    MATCH (d:Deliverable {dashboard_user_id: $uid})
    WITH d ORDER BY d.updated_at DESC LIMIT $lim
    OPTIONAL MATCH (d)-[rel]-(n)
    RETURN d.deliverable_id AS did,
           properties(d) AS dprops,
           type(rel) AS rtype,
           labels(n)[0] AS nkind,
           properties(n) AS nprops
    """
    uid = dashboard_user_id.strip()
    async with driver.session(database="neo4j") as session:
        cursor = await session.run(stmt, uid=uid, lim=lim)
        async for rec in cursor:
            did_anchor = rec.get("did")
            dp = dict(rec.get("dprops") or {})
            if did_anchor:
                sid = str(did_anchor)
                nodes[sid] = {
                    "id": sid,
                    "graph_kind": "Deliverable",
                    "label": _pick_label("Deliverable", dp | {"deliverable_id": did_anchor}),
                    "summary": str(dp.get("summary") or "")[:240],
                    "tags": dp.get("tags") or [],
                }

            nk = rec.get("nkind")
            np_props = dict(rec.get("nprops") or {})
            rtype_raw = rec.get("rtype")

            peer_id_val: str | None = None
            if nk == "Deliverable":
                peer_id_val = np_props.get("deliverable_id")
            elif nk == "Tag":
                peer_id_val = f"tg:{np_props.get('name', 'tag')}"
            elif nk == "Insight":
                peer_id_val = f"ins:{np_props.get('origin_deliverable','?')}:{np_props.get('version','')}"
            elif nk == "Reflection":
                peer_id_val = f"refl:{np_props.get('origin_deliverable','?')}:{np_props.get('version','')}"
            elif nk == "ManagerTemplate":
                slug_m = np_props.get("slug")
                peer_id_val = f"mgr:{slug_m}" if slug_m else None
            elif nk == "Task":
                peer_id_val = f"tsk:{np_props.get('task_id','?')}"

            if nk and peer_id_val is not None and str(peer_id_val) not in nodes:
                nk_s = nk or "Unknown"
                nodes[str(peer_id_val)] = {
                    "id": str(peer_id_val),
                    "graph_kind": nk_s,
                    "label": _pick_label(str(nk_s), np_props),
                    "summary": str(np_props.get("body_excerpt") or np_props.get("body") or np_props.get("summary") or "")[
                        :240
                    ],
                    "tags": np_props.get("tags") if isinstance(np_props.get("tags"), list) else [],
                }

            if did_anchor and peer_id_val and isinstance(rtype_raw, str):
                ea = str(did_anchor)
                eb = str(peer_id_val)
                ek = f"{ea}|{rtype_raw}|{eb}"
                edges[ek] = {"source": ea, "target": eb, "kind": rtype_raw}

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


async def neighbor_snapshot_for_prompt(
    *,
    deliverable_ids: list[str],
    breadth: int,
) -> list[str]:
    """Return short bullet summaries for agent conditioning."""

    ids = [d.strip() for d in deliverable_ids if len(d.strip()) >= 32][: max(1, min(breadth, 12))]
    if not ids:
        return []
    driver = await get_neo4j_driver()
    lines: list[str] = []
    cypher = """
    UNWIND $ids AS hid
    MATCH (d:Deliverable {deliverable_id: hid})
    OPTIONAL MATCH (d)-[:CORRELATES_WITH]->(peer:Deliverable)
    RETURN distinct d.deliverable_id AS did,
           d.title AS anchor_title,
           d.summary AS anchor_summary,
           collect(peer.summary)[0..3] AS peer_snips,
           collect(peer.title)[0..3] AS peer_titles
    """

    async with driver.session(database="neo4j") as session:
        res = await session.run(cypher, ids=ids)
        async for rec in res:
            title = str(rec.get("anchor_title") or "").strip()
            snippet = str(rec.get("anchor_summary") or "").strip()[:560]
            peer_titles = [str(x) for x in (rec.get("peer_titles") or []) if x]
            peer_snips = [str(x) for x in (rec.get("peer_snips") or []) if x]
            bullets: list[str] = []
            if snippet:
                bullets.append(f"- {title}: {snippet}")
            for pt, ps in zip(peer_titles[:3], peer_snips[:3], strict=False):
                if ps.strip():
                    bullets.append(f"- related · {pt}: {ps[:240]}".strip())
            lines.extend(bullets)

    return lines


__all__ = ["bounded_operator_graph_snapshot", "neighbor_snapshot_for_prompt", "persist_hive_graph_bundle"]
