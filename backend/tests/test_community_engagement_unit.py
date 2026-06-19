"""Unit tests for POS-CE community engagement policy."""

from __future__ import annotations

from app.application.services.community_engagement_policy import (
    merge_community_engagement_context,
    monitor_skill_bundle,
    reddit_urls_to_rss_feeds,
)
from app.application.services.data_monitor_wizard_service import (
    classify_monitor_niche,
    derive_data_monitor_plan,
)
from app.application.services.rubric_templates import get_rubric_template


def test_reddit_urls_to_rss_feeds_deduplicates() -> None:
    text = "Watch https://www.reddit.com/r/Beekeeping/ and https://reddit.com/r/beekeeping/new"
    feeds = reddit_urls_to_rss_feeds(text)
    assert feeds == ["https://www.reddit.com/r/beekeeping/.rss"]


def test_classify_monitor_niche_community() -> None:
    niche = classify_monitor_niche("Monitor subreddit r/Beekeeping for honey questions")
    assert niche == "community"


def test_derive_data_monitor_plan_community_binds_rss() -> None:
    plan = derive_data_monitor_plan(
        "Track https://www.reddit.com/r/LocalLLaMA/ for agent tooling questions",
        schedule_preset="24h",
    )
    assert plan.niche == "community"
    assert plan.source_type == "rss"
    assert "community-engagement-playbook" in plan.skill_bundle
    assert "engagement-candidate" in plan.topic_tags


def test_monitor_skill_bundle_community_vs_rss() -> None:
    community = monitor_skill_bundle(niche="community", source_type="rss")
    generic = monitor_skill_bundle(niche="news", source_type="rss")
    assert "community-engagement-playbook" in community
    assert "community-engagement-playbook" not in generic


def test_merge_community_engagement_context_preserves_lane_keys() -> None:
    merged = merge_community_engagement_context({"four_lane_id": "marketing_najman"})
    assert merged["four_lane_id"] == "marketing_najman"
    ce = merged["community_engagement"]
    assert ce["max_draft_replies_per_digest"] == 3
    assert ce["max_live_posts_per_day"] == 0
    assert ce["closed_review_template_id"] == "community-authenticity"


def test_community_authenticity_rubric_registered() -> None:
    template = get_rubric_template("community-authenticity")
    assert template is not None
    assert template.pass_threshold >= 0.8
