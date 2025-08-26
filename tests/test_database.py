import importlib.util
import pathlib
import sqlite3
import sys
import types

import pytest

sys.modules["psycopg2"] = types.SimpleNamespace(
    connect=lambda *args, **kwargs: None
)

sys.modules["dotenv"] = types.SimpleNamespace(
    load_dotenv=lambda *args, **kwargs: None
)

spec = importlib.util.spec_from_file_location(
    "database",
    (
        pathlib.Path(__file__)
        .resolve()
        .parents[1]
        / "page_analyzer"
        / "database.py"
    ),
)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)

OK_STATUS = 200
NOT_FOUND_STATUS = 404


class SQLiteCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cursor.close()

    def execute(self, query, params=None):
        if params is None:
            params = ()
        query = query.replace("%s", "?")
        self.cursor.execute(query, params)
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class SQLiteConnection:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.conn.commit()

    def cursor(self):
        return SQLiteCursor(self.conn.cursor())

    def commit(self):
        self.conn.commit()


@pytest.fixture
def db(monkeypatch):
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.execute(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    raw_conn.execute(
        """
        CREATE TABLE url_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INT,
            status_code INT,
            h1 TEXT,
            title TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    conn = SQLiteConnection(raw_conn)
    monkeypatch.setattr(database, "get_conn", lambda: conn)
    yield conn
    raw_conn.close()


def test_insert_and_find_url(db):
    name = "https://example.com"
    new_id = database.insert_url(name)
    row = database.find_url_by_name(name)
    assert row[0] == new_id


def test_insert_check_and_fetch_url(db):
    name = "https://example.org"
    url_id = database.insert_url(name)
    database.insert_url_check(url_id, OK_STATUS, "h1", "title", "desc")
    url_item, checks = database.fetch_url(url_id)
    assert url_item[0] == url_id
    assert checks[0][1] == OK_STATUS


def test_fetch_urls_with_last_check(db):
    id1 = database.insert_url("https://a.com")
    id2 = database.insert_url("https://b.com")
    database.insert_url_check(id1, OK_STATUS, None, None, None)
    database.insert_url_check(id2, NOT_FOUND_STATUS, None, None, None)
    urls = database.fetch_urls_with_last_check()
    assert urls[0][0] == id2
    assert urls[0][3] == NOT_FOUND_STATUS
    assert urls[1][0] == id1
    assert urls[1][3] == OK_STATUS
