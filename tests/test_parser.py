import importlib.util
import re
import sys
import types
from http import HTTPStatus

import pytest


class RequestException(Exception):
    pass


# Stub "requests" module
requests_stub = types.ModuleType("requests")
exceptions_stub = types.ModuleType("requests.exceptions")
exceptions_stub.RequestException = RequestException
requests_stub.exceptions = exceptions_stub
sys.modules["requests"] = requests_stub
sys.modules["requests.exceptions"] = exceptions_stub


# Stub "bs4" module with minimal BeautifulSoup implementation
class FakeSoup:
    def __init__(self, html, parser):
        self.html = html

    def _extract(self, tag):
        
        pattern = rf"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, self.html, re.IGNORECASE | re.DOTALL)
        if match:
            return types.SimpleNamespace(string=match.group(1).strip())
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


bs4_stub = types.ModuleType("bs4")
bs4_stub.BeautifulSoup = FakeSoup
sys.modules["bs4"] = bs4_stub


# Load parser module without importing the whole package

spec = importlib.util.spec_from_file_location(
    "parser", "page_analyzer/parser.py",
)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
fetch_html = parser.fetch_html
parse_seo = parser.parse_seo


def test_fetch_html(monkeypatch):
    class MockResponse:
        status_code = 200
        text = "<html></html>"

        def raise_for_status(self):
            pass

    def mock_get(url, timeout):
        return MockResponse()

    monkeypatch.setattr(parser.requests, "get", mock_get, raising=False)
    html, status = fetch_html("http://example.com")
    assert html == "<html></html>"
    assert status == HTTPStatus.OK


def test_fetch_html_error(monkeypatch):
    def mock_get(url, timeout):
        raise RequestException("error")

    monkeypatch.setattr(parser.requests, "get", mock_get, raising=False)
    with pytest.raises(RequestException):
        fetch_html("http://example.com")


def test_parse_seo():
    html = (
        "<html><head><title>My Title</title>"
        "<meta name='description' content='Desc'></head>"
        "<body><h1>Header</h1></body></html>"
    )
    h1, title, description = parse_seo(html)
    assert h1 == "Header"
    assert title == "My Title"
    assert description == "Desc"


def test_parse_seo_missing_tags():
    html = "<html><head></head><body></body></html>"
    h1, title, description = parse_seo(html)
    assert h1 is None
    assert title is None
    assert description is None
