"""Unit tests for LN2 loop anti-cheat."""

from __future__ import annotations

from app.application.services.loop_anti_cheat_service import (
    loop_anti_cheat_blocks_critic_pass,
    scan_output_for_anti_cheat_violations,
)


def test_anti_cheat_blocks_delete_test() -> None:
    hits = scan_output_for_anti_cheat_violations("Let's delete the failing tests to pass CI.")
    assert "delete_test_file" in hits
    assert loop_anti_cheat_blocks_critic_pass(output_text="delete the tests") is True


def test_anti_cheat_clean_output() -> None:
    assert loop_anti_cheat_blocks_critic_pass(output_text="## Verification verdict: APPROVED") is False
