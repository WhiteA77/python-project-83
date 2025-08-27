import importlib.util
import re
import sys
import types
from http import HTTPStatus
from pathlib import Path

import pytest


class RequestException(Exception):
    pass


# Stub "bs4" module with minimal BeautifulSoup implementation
class FakeSoup:
    def __init__(self, html, parser):
        self.html = html

    def _extract(self, tag):
        
        pattern = rf"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, self.html, re.IGNORECASE | re.DOTALL)
        if match:
            return types.SimpleNamespace(
                get_text=lambda strip=False, **kwargs: match.group(1).strip()
                if strip
                else match.group(1)
            )
        return None

    @property
    def h1(self):
        return self._extract("h1")

    @property
    def title(self):
        return self._extract("title")

    def find(self, tag, attrs=None):
        
        if tag == "meta" and attrs and attrs.get("name") == "description":
            pattern = r'<meta[^>]*name=["\\\']description["\\\'][^>]*content=["\\\'](.*?)["\\\']'
            match = re.search(pattern, self.html, re.IGNORECASE | re.DOTALL)
            if match:
                return types.SimpleNamespace(
                    get=lambda key, default=None: match.group(1).strip()
                )
        return None


@pytest.fixture
def parser(monkeypatch):
    requests_stub = types.ModuleType("requests")
    exceptions_stub = types.ModuleType("requests.exceptions")
    exceptions_stub.RequestException = RequestException
    requests_stub.exceptions = exceptions_stub
    monkeypatch.setitem(sys.modules, "requests", requests_stub)
    monkeypatch.setitem(sys.modules, "requests.exceptions", exceptions_stub)

    bs4_stub = types.ModuleType("bs4")
    bs4_stub.BeautifulSoup = FakeSoup
    monkeypatch.setitem(sys.modules, "bs4", bs4_stub)

    parser_path = (
        Path(__file__).resolve().parents[1] / "page_analyzer" / "parser.py"
    )
    spec = importlib.util.spec_from_file_location("parser", parser_path)
    parser_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser_module)
    return parser_module


def test_fetch_html(parser, monkeypatch):
    class MockResponse:
        status_code = 200
        text = "<html></html>"

        def raise_for_status(self):
            pass

    def mock_get(url, timeout):
        return MockResponse()

    monkeypatch.setattr(parser.requests, "get", mock_get, raising=False)
    html, status = parser.fetch_html("http://example.com")
    assert html == "<html></html>"
    assert status == HTTPStatus.OK


def test_fetch_html_error(parser, monkeypatch):
    def mock_get(url, timeout):
        raise RequestException("error")

    monkeypatch.setattr(parser.requests, "get", mock_get, raising=False)
    with pytest.raises(RequestException):
        parser.fetch_html("http://example.com")


def test_parse_seo(parser):
    html = (
        "<html><head><title>My Title</title>"
        "<meta name='description' content='Desc'></head>"
        "<body><h1>Header</h1></body></html>"
    )
    h1, title, description = parser.parse_seo(html)
    assert h1 == "Header"
    assert title == "My Title"
    assert description == "Desc"


def test_parse_seo_missing_tags(parser):
    html = "<html><head></head><body></body></html>"
    h1, title, description = parser.parse_seo(html)
    assert h1 is None
    assert title is None
    assert description is None
