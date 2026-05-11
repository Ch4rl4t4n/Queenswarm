"""Async Neo4j driver for hive knowledge graphs, imitation chains, and semantic decay."""

from __future__ import annotations

import uuid
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError

from app.core.config import settings

_driver: AsyncDriver | None = None


def _build_driver() -> AsyncDriver:
    """Instantiate a singleton AsyncDriver wired to hive settings."""

    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def get_neo4j_driver() -> AsyncDriver:
    """Return the application-wide Neo4j async driver (lazy singleton)."""

    global _driver
    if _driver is None:
        _driver = _build_driver()
    return _driver


async def create_knowledge_node(
    content: str,
    source: str,
    confidence: float,
    topic_tags: list[str],
) -> str:
    """Persist a knowledge node and return its stable application id.

    Args:
        content: Normalized text stored on the node.
        source: Provenance label (URL, agent, dataset).
        confidence: Initial confidence score in ``[0, 1]``.
        topic_tags: Tags used for graph recall and decay heuristics.

    Returns:
        String ``id`` property assigned to the created node.

    Raises:
        Neo4jError: When the create transaction fails.
    """

    node_id = str(uuid.uuid4())
    driver = await get_neo4j_driver()
    cypher = """
    CREATE (n:KnowledgeNode {
        id: $id,
        content: $content,
        source: $source,
        confidence: $confidence,
        topic_tags: $topic_tags,
        updated_at: datetime()
    })
    RETURN n.id AS id
    """
    async with driver.session() as session:
        result = await session.run(
            cypher,
            id=node_id,
            content=content,
            source=source,
            confidence=confidence,
            topic_tags=topic_tags,
        )
        record = await result.single()
        if record is None:
            raise Neo4jError("Failed to create KnowledgeNode.")
        rid = record["id"]
        if rid is None:
            raise Neo4jError("Missing id on created KnowledgeNode.")
        return str(rid)


async def link_nodes(node_a_id: str, node_b_id: str, relation: str) -> None:
    """Connect two hive entities by deterministic ``id`` with a RELATES_TO edge kind."""

    driver = await get_neo4j_driver()
    cypher = """
    MATCH (a {id: $node_a}), (b {id: $node_b})
    MERGE (a)-[r:RELATES_TO]->(b)
    SET r.kind = $relation
    RETURN r
    """
    async with driver.session() as session:
        await session.run(cypher, node_a=node_a_id, node_b=node_b_id, relation=relation)


async def find_related(topic: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return knowledge nodes matching ``topic`` against structured topic tags."""

    driver = await get_neo4j_driver()
    needle = topic.lower()
    cypher = """
    MATCH (n:KnowledgeNode)
    WHERE ANY(tag IN COALESCE(n.topic_tags, [])
              WHERE toLower(toString(tag)) CONTAINS $needle)
    RETURN n.id AS id,
           n.content AS content,
           n.source AS source,
           n.confidence AS confidence,
           n.topic_tags AS topic_tags
    LIMIT $limit
    """
    async with driver.session() as session:
        result = await session.run(cypher, needle=needle, limit=int(limit))
        rows: list[dict[str, Any]] = []
        async for record in result:
            rows.append(dict(record.data()))
        return rows


async def decay_old_nodes(days: int = 14) -> None:
    """Reduce confidence for KnowledgeNode rows older than ``days``.

    Applies a multiplicative decay (50%) gated on ``updated_at`` relative to Neo4j ``datetime()``,
    aligning with Recipe Library TTL heuristics and global hive compaction.

    Args:
        days: Age cutoff matching ``memory_decay_days`` from settings when invoked by jobs.
    """

    driver = await get_neo4j_driver()
    cypher = """
    MATCH (n:KnowledgeNode)
    WHERE n.updated_at < datetime() - duration({days: $days})
    SET n.confidence = coalesce(n.confidence, 1.0) * 0.5,
        n.updated_at = datetime()
    """
    async with driver.session() as session:
        await session.run(cypher, days=int(days))


async def record_imitation(copier_id: str, copied_id: str, recipe_id: str) -> None:
    """Record a Maynard-Cross imitation edge between hive agents for graph analytics."""

    driver = await get_neo4j_driver()
    cypher = """
    MERGE (copier:HiveAgent {agent_id: $copier_id})
    MERGE (copied:HiveAgent {agent_id: $copied_id})
    MERGE (copier)-[:IMITATED {recipe_id: $recipe_id, recorded_at: datetime()}]->(copied)
    """
    async with driver.session() as session:
        await session.run(
            cypher,
            copier_id=copier_id,
            copied_id=copied_id,
            recipe_id=recipe_id,
        )


async def close_neo4j() -> None:
    """Close the Neo4j driver during FastAPI shutdown."""

    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
