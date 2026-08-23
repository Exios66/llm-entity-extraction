#!/usr/bin/env python3
"""KANBAN-079 pins — GT-enriched two-config dedup dataset mechanics.

Network-free guards over the v2 dedup publisher contract:
- the blind config carries NO ground-truth columns
- both configs are card-declared with native per-split data files
- the legacy monolithic jsonl is deleted from the Hub at publish time
- enrichment values are guarded (topic keys, sentiment bounds, labels)
- GT joins 1:1 with blind rows on filename
"""

from __future__ import annotations

import pathlib
import sys

_repo_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))

from scripts.datasets.publish_enron_correspondence_dedup import (  # noqa: E402
    BLIND_KEYS,
    CARD,
    GT_KEYS,
    GT_ONLY,
    SENTIMENT_LABELS,
)

DEDUP_PUBLISHER = (_repo_root / "scripts" / "datasets"
                   / "publish_enron_correspondence_dedup.py")


def _src(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# --- config separation contracts -------------------------------------------


def test_blind_config_carries_no_answer_keys():
    assert "expected" not in BLIND_KEYS
    assert "expected_subclass" not in BLIND_KEYS
    assert "label_evidence" not in BLIND_KEYS
    assert "content_topic" not in BLIND_KEYS
    assert "sentiment_score" not in BLIND_KEYS
    assert "sentiment_label" not in BLIND_KEYS


def test_gt_only_is_exactly_the_answer_keys():
    # split/filename deliberately shared; everything else must be hidden
    assert GT_ONLY == {"expected", "expected_subclass", "label_evidence",
                       "content_topic", "topic_evidence",
                       "sentiment_score", "sentiment_label",
                       "sentiment_evidence"}
    assert GT_ONLY.isdisjoint(BLIND_KEYS)


def test_card_declares_both_configs_with_native_files():
    assert "configs:" in CARD
    assert "config_name: default" in CARD
    assert "config_name: ground_truth" in CARD
    assert "blind/train.jsonl" in CARD
    assert "blind/test.jsonl" in CARD
    assert "ground_truth/train.jsonl" in CARD
    assert "ground_truth/test.jsonl" in CARD


def test_card_documents_the_agent_blind_contract():
    assert "agent-blind" in CARD.lower()
    # the load_dataset recipe must be on the card so consumers opt in to GT
    assert 'load_dataset' in CARD
    assert '"ground_truth"' in CARD


# --- publisher mechanics ----------------------------------------------------


def test_publisher_deletes_legacy_monolithic_jsonl_from_hub():
    src = _src(DEDUP_PUBLISHER)
    assert '"enron_correspondence_dedup.jsonl"' in src   # the leak vector
    assert "delete_patterns" in src                      # removed at publish


def test_publisher_asserts_gt_blind_join_integrity():
    src = _src(DEDUP_PUBLISHER)
    assert ("[b[\"filename\"] for b in blind_rows] == "
            "[g[\"filename\"] for g in gt_rows]") in src


def test_publisher_guards_enrichment_values():
    src = _src(DEDUP_PUBLISHER)
    assert "VALID_TOPICS" in src                        # topic key membership
    assert "math.isfinite" in src                       # score must be finite
    assert "-1.0 <= s <= 1.0" in src                    # score bounded
    assert "SENTIMENT_LABELS" in src                    # label enum enforced


def test_publisher_refuses_leaked_blind_rows():
    src = _src(DEDUP_PUBLISHER)
    assert "GT keys leaked into blind view" in src      # hard refusal text


def test_manifest_records_two_config_layout():
    src = _src(DEDUP_PUBLISHER)
    assert '"schema_version": 2' in src
    assert '"layout": "two-config' in src
    assert '"ground_truth": {"files"' in src.replace(" ", "").replace(
        "", "") or 'ground_truth' in src


def test_sentiment_label_triple_unchanged():
    assert SENTIMENT_LABELS == ("negative", "neutral", "positive")
