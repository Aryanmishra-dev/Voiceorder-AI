"""Tests for order service helpers."""

import pytest
from fastapi import HTTPException

from app.services.order_service import normalize_status


def test_normalize_status_accepts_valid_status():
    assert normalize_status(" CONFIRMED ") == "confirmed"


def test_normalize_status_rejects_invalid_status():
    with pytest.raises(HTTPException):
        normalize_status("unknown")
