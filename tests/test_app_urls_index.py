import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "test_app_index", Path(__file__).resolve().parent / "test_app_index.py"
)
test_app_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_app_index)

app = test_app_index.app
OK_STATUS = test_app_index.OK_STATUS


@pytest.fixture()
def client():
    return app.app.test_client()


def test_urls_index_renders_template_and_data(monkeypatch, client):
    sample_urls = [(1, "https://example.com", None, None)]
    monkeypatch.setattr(app, "fetch_urls_with_last_check", lambda: sample_urls)

    rendered = {}

    def fake_render(template_name, **kwargs):
        rendered["name"] = template_name
        rendered["urls"] = kwargs.get("urls")
        return str(kwargs.get("urls"))

    monkeypatch.setattr(app, "render_template", fake_render)

    response = client.get("/urls")

    assert response.status_code == OK_STATUS
    assert rendered["name"] == "urls.html"
    assert rendered["urls"] == sample_urls
    assert str(sample_urls).encode() in response.data