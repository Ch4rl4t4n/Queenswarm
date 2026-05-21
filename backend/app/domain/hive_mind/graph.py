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
    if kind == "VaultDocument":
        return str(props.get("title") or props.get("rel_path") or "document")[:180]
    if kind == "VaultFolder":
        return str(props.get("label") or props.get("path") or "folder")[:180]
    if kind == "GraphifyBatch":
        return str(props.get("folder_label") or f"Batch {props.get('batch_id', '')[:8]}")[:180]
    return kind


def _project_shape_peer_id(*, kind: str, props: dict[str, Any]) -> str | None:
    """Stable React Flow node id for project-shape graph kinds."""

    if kind == "VaultFolder":
        path = props.get("path")
        return f"vf:{path}" if path else None
    if kind == "VaultDocument":
        doc_id = props.get("doc_id")
        return str(doc_id) if doc_id else None
    if kind == "GraphifyBatch":
        batch_id = props.get("batch_id")
        return f"gb:{batch_id}" if batch_id else None
    if kind == "Tag":
        name = props.get("name")
        return f"tg:{name}" if name else None
    return None


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


async def bounded_tenant_project_shape_snapshot(
    *,
    tenant_id: uuid.UUID,
    limit_nodes: int,
) -> dict[str, Any]:
    """Tenant-scoped Auto-Graphify folder tree — VaultFolder → VaultDocument constellation."""

    driver = await get_neo4j_driver()
    tid = str(tenant_id)
    lim = max(4, min(int(limit_nodes), 200))
    folder_lim = max(2, min(lim // 3, 24))
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    stmt = """
    MATCH (f:VaultFolder {tenant_id: $tid})
    WITH f ORDER BY f.updated_at DESC LIMIT $folder_lim
    OPTIONAL MATCH (f)-[contains:CONTAINS]->(d:VaultDocument {tenant_id: $tid})
    OPTIONAL MATCH (b:GraphifyBatch {tenant_id: $tid})-[:ROOTED_IN]->(f)
    OPTIONAL MATCH (d)-[tagged:TAGGED_AS]->(tg:Tag)
    RETURN f.path AS folder_path,
           properties(f) AS fprops,
           labels(d)[0] AS dkind,
           properties(d) AS dprops,
           type(contains) AS contains_kind,
           labels(b)[0] AS bkind,
           properties(b) AS bprops,
           type(tagged) AS tag_kind,
           labels(tg)[0] AS tgkind,
           properties(tg) AS tgprops
    """
    async with driver.session(database="neo4j") as session:
        cursor = await session.run(stmt, tid=tid, folder_lim=folder_lim)
        async for rec in cursor:
            fprops = dict(rec.get("fprops") or {})
            folder_path = rec.get("folder_path") or fprops.get("path")
            if folder_path:
                fid = f"vf:{folder_path}"
                if fid not in nodes:
                    nodes[fid] = {
                        "id": fid,
                        "graph_kind": "VaultFolder",
                        "label": _pick_label("VaultFolder", fprops | {"path": folder_path}),
                        "summary": str(folder_path)[:240],
                        "tags": [],
                        "rel_path": str(folder_path),
                    }

            bkind = rec.get("bkind")
            bprops = dict(rec.get("bprops") or {})
            if bkind == "GraphifyBatch":
                batch_id = bprops.get("batch_id")
                if batch_id:
                    bid = f"gb:{batch_id}"
                    if bid not in nodes:
                        nodes[bid] = {
                            "id": bid,
                            "graph_kind": "GraphifyBatch",
                            "label": _pick_label("GraphifyBatch", bprops),
                            "summary": f"{bprops.get('file_count', 0)} files ingested",
                            "tags": ["auto_graphify"],
                            "batch_id": str(batch_id),
                        }
                    if folder_path:
                        ek = f"{bid}|ROOTED_IN|vf:{folder_path}"
                        edges[ek] = {"source": bid, "target": f"vf:{folder_path}", "kind": "ROOTED_IN"}

            dkind = rec.get("dkind")
            dprops = dict(rec.get("dprops") or {})
            if dkind == "VaultDocument":
                doc_id = dprops.get("doc_id")
                if doc_id:
                    did = str(doc_id)
                    if did not in nodes:
                        nodes[did] = {
                            "id": did,
                            "graph_kind": "VaultDocument",
                            "label": _pick_label("VaultDocument", dprops),
                            "summary": str(dprops.get("excerpt") or dprops.get("rel_path") or "")[:240],
                            "tags": list(dprops.get("tags") or [])[:16],
                            "rel_path": str(dprops.get("rel_path") or ""),
                        }
                    if folder_path:
                        ek = f"vf:{folder_path}|CONTAINS|{did}"
                        edges[ek] = {"source": f"vf:{folder_path}", "target": did, "kind": "CONTAINS"}

            tgkind = rec.get("tgkind")
            tgprops = dict(rec.get("tgprops") or {})
            if tgkind == "Tag" and dprops.get("doc_id"):
                tag_id = _project_shape_peer_id(kind="Tag", props=tgprops)
                doc_id = str(dprops.get("doc_id"))
                if tag_id and doc_id in nodes:
                    if tag_id not in nodes:
                        nodes[tag_id] = {
                            "id": tag_id,
                            "graph_kind": "Tag",
                            "label": _pick_label("Tag", tgprops),
                            "summary": "",
                            "tags": [],
                        }
                    ek = f"{doc_id}|TAGGED_AS|{tag_id}"
                    edges[ek] = {"source": doc_id, "target": tag_id, "kind": "TAGGED_AS"}

            if len(nodes) >= lim:
                break

    return {
        "nodes": list(nodes.values())[:lim],
        "edges": list(edges.values()),
        "tenant_id": tid,
        "shape": "project",
    }


async def vault_document_recall_for_prompt(
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int = 3,
) -> list[str]:
    """Return ranked VaultDocument bullets for selective recall (Auto-Graphify lane)."""

    from app.application.services.selective_recall import query_tokens

    tokens = query_tokens(query)
    if not tokens:
        return []

    driver = await get_neo4j_driver()
    tid = str(tenant_id)
    lim = max(1, min(int(limit), 8))
    stmt = """
    MATCH (d:VaultDocument {tenant_id: $tid})
    RETURN d.title AS title,
           d.excerpt AS excerpt,
           d.rel_path AS rel_path,
           coalesce(d.tags, []) AS tags,
           d.updated_at AS updated_at
    ORDER BY d.updated_at DESC
    LIMIT $scan_lim
    """
    scan_lim = max(lim * 6, 12)
    candidates: list[tuple[float, str]] = []

    async with driver.session(database="neo4j") as session:
        cursor = await session.run(stmt, tid=tid, scan_lim=scan_lim)
        async for rec in cursor:
            title = str(rec.get("title") or "").strip()
            excerpt = str(rec.get("excerpt") or "").strip()
            rel_path = str(rec.get("rel_path") or "").strip()
            tags = [str(t).lower() for t in (rec.get("tags") or []) if str(t).strip()]
            hay = " ".join([title, excerpt, rel_path, " ".join(tags)]).lower()
            overlap = sum(1 for token in tokens if token in hay)
            if overlap <= 0:
                continue
            score = overlap / max(1, len(tokens))
            line = f"- vault · {title or rel_path}: {(excerpt or rel_path)[:220]}"
            candidates.append((score, line))

    if not candidates:
        async with driver.session(database="neo4j") as session:
            cursor = await session.run(stmt, tid=tid, scan_lim=lim)
            async for rec in cursor:
                title = str(rec.get("title") or "").strip()
                excerpt = str(rec.get("excerpt") or "").strip()
                rel_path = str(rec.get("rel_path") or "").strip()
                line = f"- vault · {title or rel_path}: {(excerpt or rel_path)[:220]}"
                candidates.append((0.1, line))

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return [line for _, line in candidates[:lim]]


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


async def persist_graphify_ingest_bundle(
    *,
    tenant_id: uuid.UUID,
    batch_id: uuid.UUID,
    folder_label: str,
    files: list[dict[str, Any]],
) -> int:
    """Upsert `:GraphifyBatch`, `:VaultFolder`, and `:VaultDocument` nodes for folder ingest."""

    if not files:
        return 0

    driver = await get_neo4j_driver()
    tid = str(tenant_id)
    bid = str(batch_id)
    folder_path = f"graphify/{tid}/{bid}"
    created = 0

    async with driver.session(database="neo4j") as session:
        await session.run(
            """
            MERGE (b:GraphifyBatch {batch_id: $bid})
            SET b.tenant_id = $tid,
                b.folder_label = $label,
                b.file_count = $count,
                b.updated_at = datetime()
            MERGE (f:VaultFolder {path: $folder_path, tenant_id: $tid})
            SET f.label = $label,
                f.updated_at = datetime()
            MERGE (b)-[:ROOTED_IN]->(f)
            """,
            bid=bid,
            tid=tid,
            label=folder_label[:240],
            count=len(files),
            folder_path=folder_path,
        )
        created += 2

        for row in files:
            doc_id = str(row.get("doc_id") or "")
            if not doc_id:
                continue
            rel_path = str(row.get("rel_path") or "")[:480]
            title = str(row.get("title") or rel_path or "document")[:500]
            excerpt = str(row.get("excerpt") or "")[:2600]
            tags = [str(t)[:160] for t in (row.get("tags") or []) if str(t).strip()][:16]
            await session.run(
                """
                MERGE (d:VaultDocument {doc_id: $doc_id})
                SET d.tenant_id = $tid,
                    d.batch_id = $bid,
                    d.rel_path = $rel_path,
                    d.title = $title,
                    d.excerpt = $excerpt,
                    d.tags = $tags,
                    d.updated_at = datetime()
                WITH d
                MATCH (f:VaultFolder {path: $folder_path, tenant_id: $tid})
                MERGE (f)-[:CONTAINS]->(d)
                WITH d
                MATCH (b:GraphifyBatch {batch_id: $bid})
                MERGE (b)-[:INGESTED]->(d)
                """,
                doc_id=doc_id,
                tid=tid,
                bid=bid,
                rel_path=rel_path,
                title=title,
                excerpt=excerpt,
                tags=tags,
                folder_path=folder_path,
            )
            created += 1
            for tag in tags:
                tag_norm = tag.strip().lower().replace(" ", "_")
                if len(tag_norm) < 2:
                    continue
                await session.run(
                    """
                    MERGE (tg:Tag {name: $name})
                    SET tg.updated_at = datetime()
                    WITH tg
                    MATCH (d:VaultDocument {doc_id: $doc_id})
                    MERGE (d)-[:TAGGED_AS]->(tg)
                    """,
                    name=tag_norm[:160],
                    doc_id=doc_id,
                )

    return created


__all__ = [
    "bounded_operator_graph_snapshot",
    "bounded_tenant_project_shape_snapshot",
    "neighbor_snapshot_for_prompt",
    "persist_graphify_ingest_bundle",
    "persist_hive_graph_bundle",
    "vault_document_recall_for_prompt",
]
