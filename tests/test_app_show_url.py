import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from test_app_index import app

REDIRECT_STATUS = 302


def test_show_url_not_found_redirects(monkeypatch):
    messages = []

    def fake_flash(message, category=None):
        messages.append((message, category))

    monkeypatch.setattr(app, "fetch_url", lambda id: (None, []))
    monkeypatch.setattr(app, "flash", fake_flash)

    response = app.show_url(1)

    assert response.status_code == REDIRECT_STATUS
    assert response.headers["Location"] == "/urls"
    assert messages == [("Страница не найдена", "danger")]


def test_show_url_renders_template(monkeypatch):
    rendered = {}
    url_record = (1, "https://example.com", "2024-01-01")
    checks = [(1, 200, "h1", "title", "desc", "2024-01-02")]

    def fake_render(template_name, **kwargs):
        rendered["name"] = template_name
        rendered["kwargs"] = kwargs
        return ""

    monkeypatch.setattr(app, "fetch_url", lambda id: (url_record, checks))
    monkeypatch.setattr(app, "render_template", fake_render)

    response = app.show_url(1)

    assert response == ""
    assert rendered["name"] == "show_url.html"
    assert rendered["kwargs"]["url"] == url_record
    assert rendered["kwargs"]["checks"] == checks