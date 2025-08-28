import importlib
import sys
import types
from pathlib import Path

import pytest

validators_stub = types.ModuleType("validators")
validators_stub.url = lambda value: value.startswith("http")
sys.modules["validators"] = validators_stub

module_path = Path(__file__).resolve().parents[1] / "page_analyzer" / "url_utils.py"
spec = importlib.util.spec_from_file_location("url_utils", module_path)
url_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(url_utils)

validate_url = url_utils.validate_url
normalize_url = url_utils.normalize_url


def test_validate_url():
    assert validate_url("https://example.com")
    assert not validate_url("invalid-url")

    long_url = "http://" + "a" * 250
    assert not validate_url(long_url)

    assert not validate_url("https://example.com", max_length=10)


def test_normalize_url():
    assert normalize_url("https://example.com/path?q=1") == "https://example.com"
    assert normalize_url("http://example.com") == "http://example.com"