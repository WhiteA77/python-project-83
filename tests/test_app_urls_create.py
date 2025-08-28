import pytest
import test_app_index as app_index

from page_analyzer import database, url_utils

app = app_index.app

FOUND_STATUS = 302
UNPROCESSABLE_ENTITY_STATUS = 422
URLS = "/urls"

MSG_INVALID = "Некорректный URL"
MSG_EXISTS = "Страница уже существует"
MSG_ADDED = "Страница успешно добавлена"


@pytest.fixture()
def client():
    return app.app.test_client()


def test_invalid_url(monkeypatch, client):
    flashes = []

    def _flash(msg, category=None):
        flashes.append((msg, category))

    def _invalid(_url):
        return False

    def _normalize(url):
        calls["normalize"] += 1
        return url

    def _find(_name):
        calls["find"] += 1

    def _insert(_name):
        calls["insert"] += 1
        return 1

    calls = {"find": 0, "insert": 0, "normalize": 0}
    set_ = monkeypatch.setattr

    set_(app, "flash", _flash)
    set_(url_utils, "validate_url", _invalid)
    set_(app, "validate_url", url_utils.validate_url)
    set_(url_utils, "normalize_url", _normalize)
    set_(app, "normalize_url", _normalize)
    set_(database, "find_url_by_name", _find)
    set_(app, "find_url_by_name", _find)
    set_(database, "insert_url", _insert)
    set_(app, "insert_url", _insert)

    response = client.post("/urls", data={"url": "bad"})

    assert response.status_code == UNPROCESSABLE_ENTITY_STATUS
    assert (MSG_INVALID, "danger") in flashes
    assert calls["find"] == 0
    assert calls["insert"] == 0
    assert calls["normalize"] == 0


def test_existing_url(monkeypatch, client):
    flashes = []

    def _flash(msg, category=None):
        flashes.append((msg, category))

    def _valid(_url):
        return True

    def _same(url):
        return url

    def _find_existing(_name):
        return (5,)

    insert_called = {"value": False}

    def _insert(_name):
        insert_called["value"] = True
        return 10

    set_ = monkeypatch.setattr
    set_(app, "flash", _flash)
    set_(url_utils, "validate_url", _valid)
    set_(app, "validate_url", url_utils.validate_url)
    set_(url_utils, "normalize_url", _same)
    set_(app, "normalize_url", url_utils.normalize_url)
    set_(database, "find_url_by_name", _find_existing)
    set_(app, "find_url_by_name", database.find_url_by_name)
    set_(database, "insert_url", _insert)
    set_(app, "insert_url", _insert)

    response = client.post(
        "/urls",
        data={"url": "http://example.com"},
        follow_redirects=False,
    )

    assert response.status_code == FOUND_STATUS
    assert response.headers["Location"].endswith(f"{URLS}/5")
    assert (MSG_EXISTS, "info") in flashes
    assert insert_called["value"] is False


def test_new_url(monkeypatch, client):
    flashes = []

    def _flash(msg, category=None):
        flashes.append((msg, category))

    def _valid(_url):
        return True

    def _same(url):
        return url

    def _find_none(_name):
        return None

    def _insert_new(_name):
        return 7

    set_ = monkeypatch.setattr
    set_(app, "flash", _flash)
    set_(url_utils, "validate_url", _valid)
    set_(app, "validate_url", url_utils.validate_url)
    set_(url_utils, "normalize_url", _same)
    set_(app, "normalize_url", url_utils.normalize_url)
    set_(database, "find_url_by_name", _find_none)
    set_(app, "find_url_by_name", database.find_url_by_name)
    set_(database, "insert_url", _insert_new)
    set_(app, "insert_url", database.insert_url)

    response = client.post(
        "/urls",
        data={"url": "http://new.com"},
        follow_redirects=False,
    )

    assert response.status_code == FOUND_STATUS
    assert response.headers["Location"].endswith(f"{URLS}/7")
    assert (MSG_ADDED, "success") in flashes
