"""Tests for LLM service helpers."""

from app.services.llm_service import is_vague_response


def test_is_vague_response_detects_acknowledgments():
    assert is_vague_response("ok") is True
    assert is_vague_response("yeah.") is True


def test_is_vague_response_allows_substantive_answers():
    assert is_vague_response("I want chocolate cake") is False
