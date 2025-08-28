import importlib.util
import sys
import types
from pathlib import Path

import pytest

ns = types.SimpleNamespace
sys.modules["psycopg2"] = ns(connect=lambda *_, **__: None)
sys.modules["dotenv"] = ns(load_dotenv=lambda *_, **__: None)

validators_stub = types.ModuleType("validators")
validators_stub.url = lambda value: value.startswith("http")
sys.modules["validators"] = validators_stub

requests_stub = types.ModuleType("requests")
requests_stub.get = lambda *args, **kwargs: None
exceptions_stub = types.ModuleType("requests.exceptions")
exceptions_stub.RequestException = Exception
requests_stub.exceptions = exceptions_stub
sys.modules["requests"] = requests_stub
sys.modules["requests.exceptions"] = exceptions_stub

bs4_stub = types.ModuleType("bs4")
bs4_stub.BeautifulSoup = lambda *args, **kwargs: None
sys.modules["bs4"] = bs4_stub

_flask = types.ModuleType("flask")
_flask.current_app = None


class Response:
    def __init__(self, data="", status=200, headers=None):
        self.data = data.encode() if isinstance(data, str) else data
        self.status_code = status
        self.headers = headers or {}


class Request:
    def __init__(self):
        self.method = "GET"
        self.form = {}


request = Request()


class Flask:
    def __init__(self, name):
        self.routes = {}
        self.url_map = {}
        self.config = {}
        _flask.current_app = self

    def route(self, path, methods=None):
        methods = [m.upper() for m in (methods or ["GET"])]

        def decorator(func):
            endpoint = func.__name__
            self.url_map[endpoint] = path
            for m in methods:
                self.routes[(path, m)] = func
            return func

        return decorator

    def get(self, path):
        return self.route(path, methods=["GET"])

    def post(self, path):
        return self.route(path, methods=["POST"])

    def test_client(self):
        app = self

        class Client:
            def open(self, path, method="GET", data=None):
                request.method = method
                request.form = data or {}
                func = app.routes[(path, method)]
                result = func()
                if isinstance(result, Response):
                    return result
                if isinstance(result, tuple):
                    body, status = result
                    return Response(body, status)
                return Response(result)

            def get(self, path):
                return self.open(path, "GET")

            def post(self, path, data=None, *, follow_redirects=False):
                return self.open(path, "POST", data)

        return Client()


def url_for(endpoint, **values):
    path = _flask.current_app.url_map.get(endpoint, "")
    for key, value in values.items():
        path = path.replace(f"<int:{key}>", str(value))
        path = path.replace(f"<{key}>", str(value))
    return path


def redirect(location, code=302):
    return Response("", status=code, headers={"Location": location})


def flash(message, category=None):
    pass


def render_template(template_name, **kwargs):
    return ""


_flask.Flask = Flask
_flask.redirect = redirect
_flask.render_template = render_template
_flask.request = request
_flask.url_for = url_for
_flask.flash = flash
_flask.Response = Response
sys.modules["flask"] = _flask

package_dir = Path(__file__).resolve().parents[1] / "page_analyzer"
page_pkg = types.ModuleType("page_analyzer")
page_pkg.__path__ = [str(package_dir)]
sys.modules["page_analyzer"] = page_pkg

app_path = package_dir / "app.py"
spec = importlib.util.spec_from_file_location("page_analyzer.app", app_path)
app = importlib.util.module_from_spec(spec)
sys.modules["page_analyzer.app"] = app
spec.loader.exec_module(app)

OK_STATUS = 200
TEMP_REDIRECT_STATUS = 307


@pytest.fixture()
def client():
    return app.app.test_client()


def test_index_get_renders_template(monkeypatch, client):
    rendered = {}

    def fake_render(template_name, *args, **kwargs):
        rendered["name"] = template_name
        return ""

    monkeypatch.setattr(app, "render_template", fake_render)

    response = client.get("/")
    assert response.status_code == OK_STATUS
    assert rendered["name"] == "index.html"


def test_index_post_redirects(client):
    response = client.post("/", follow_redirects=False)
    assert response.status_code == TEMP_REDIRECT_STATUS
    assert response.headers["Location"].endswith("/urls")