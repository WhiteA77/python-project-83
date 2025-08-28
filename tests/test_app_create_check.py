import importlib.util
from pathlib import Path

REDIRECT = 302
HTTP_OK = 200
DEFAULT_TIMEOUT = 10

EXAMPLE_ID_1 = 1
EXAMPLE_ID_2 = 2
INITIAL_CALL_COUNT = 0

EXAMPLE_URL = "https://example.com"
EXAMPLE_HTML = "<h1>h</h1>"

LOCATION_URLS = "/urls"
LOCATION_URLS_ID_1 = "/urls/1"
LOCATION_URLS_ID_2 = "/urls/2"

MSG_NOT_FOUND = "Сайт не найден"
MSG_SUCCESS = "Страница успешно проверена"
MSG_ERROR = "Произошла ошибка при проверке"


spec = importlib.util.spec_from_file_location(
    "test_app_index", Path(__file__).resolve().parent / "test_app_index.py"
)
index_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(index_module)
app = index_module.app


def test_missing_url_redirects(monkeypatch):
    messages = []

    def fake_flash(message, category=None):
        messages.append((message, category))

    def fake_fetch_url(_id):
        assert _id == EXAMPLE_ID_1
        return None, []

    def never_called(*args, **kwargs):
        raise AssertionError("should not be called")

    monkeypatch.setattr(app, "flash", fake_flash)
    monkeypatch.setattr(app, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(app, "fetch_html", never_called)
    monkeypatch.setattr(app, "parse_seo", never_called)
    monkeypatch.setattr(app, "insert_url_check", never_called)

    response = app.create_check(EXAMPLE_ID_1)

    assert response.status_code == REDIRECT
    assert response.headers["Location"].endswith(LOCATION_URLS)
    assert messages == [(MSG_NOT_FOUND, "danger")]


def test_successful_check(monkeypatch):
    messages = []
    inserted = {}

    def fake_flash(message, category=None):
        messages.append((message, category))

    def fake_fetch_url(_id):
        assert _id == EXAMPLE_ID_1
        return (EXAMPLE_ID_1, EXAMPLE_URL), []

    def fake_fetch_html(url, timeout):
        assert url == EXAMPLE_URL
        assert timeout == DEFAULT_TIMEOUT
        return EXAMPLE_HTML, HTTP_OK

    def fake_parse_seo(html):
        assert html == EXAMPLE_HTML
        return "h", "title", "desc"

    def fake_insert_url_check(url_id, status_code, h1, title, description):
        inserted["data"] = (url_id, status_code, h1, title, description)

    monkeypatch.setattr(app, "flash", fake_flash)
    monkeypatch.setattr(app, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(app, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(app, "parse_seo", fake_parse_seo)
    monkeypatch.setattr(app, "insert_url_check", fake_insert_url_check)

    response = app.create_check(EXAMPLE_ID_1)

    assert response.status_code == REDIRECT
    assert response.headers["Location"].endswith(LOCATION_URLS_ID_1)
    assert inserted["data"] == (EXAMPLE_ID_1, HTTP_OK, "h", "title", "desc")
    assert messages == [(MSG_SUCCESS, "success")]


def test_request_exception(monkeypatch):
    messages = []
    called = {"count": INITIAL_CALL_COUNT}

    def fake_flash(message, category=None):
        messages.append((message, category))

    def fake_fetch_url(_id):
        assert _id == EXAMPLE_ID_2
        return (EXAMPLE_ID_2, EXAMPLE_URL), []

    def failing_fetch_html(*args, **kwargs):
        raise app.RequestException("boom")

    def fake_insert_url_check(*args, **kwargs):
        called["count"] += 1

    def never_called(*args, **kwargs):
        raise AssertionError("should not be called")

    monkeypatch.setattr(app, "flash", fake_flash)
    monkeypatch.setattr(app, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(app, "fetch_html", failing_fetch_html)
    monkeypatch.setattr(app, "parse_seo", never_called)
    monkeypatch.setattr(app, "insert_url_check", fake_insert_url_check)

    response = app.create_check(EXAMPLE_ID_2)

    assert response.status_code == REDIRECT
    assert response.headers["Location"].endswith(LOCATION_URLS_ID_2)
    assert called["count"] == INITIAL_CALL_COUNT
    assert messages == [(MSG_ERROR, "danger")]
