"""Tests for the vision-classifier response parsers (no network)."""

from src.classifier import (
    VALID_CLASSES,
    clean_prediction,
    extract_confidence,
    extract_runner_up,
)


def test_valid_classes():
    assert "contract" in VALID_CLASSES
    assert len(VALID_CLASSES) == 6


def test_clean_prediction_tagged():
    assert clean_prediction("Some text <label>contract</label> more text") == "contract"


def test_clean_prediction_plain_line():
    assert clean_prediction("Let me think...\n\ncontract") == "contract"


def test_clean_prediction_word_boundary():
    assert clean_prediction("This document is a contract because...") == "contract"


def test_clean_prediction_empty():
    assert clean_prediction(None) == ""
    assert clean_prediction("") == ""


def test_clean_prediction_no_match_returns_raw():
    assert clean_prediction("no class here") == "no class here"


def test_extract_runner_up():
    text = "Not a contract. My runner-up: correspondence"
    assert extract_runner_up(text) == "correspondence"


def test_extract_runner_up_missing():
    assert extract_runner_up("no runner up mentioned") == ""


def test_extract_confidence_tag():
    assert extract_confidence("<confidence>85</confidence>") == 0.85


def test_extract_confidence_plain_line():
    assert extract_confidence("Confidence:\n70") == 0.7


def test_extract_confidence_out_of_range():
    assert extract_confidence("<confidence>150</confidence>") == 1.0


def test_extract_confidence_none():
    assert extract_confidence("no number here") is None
