import os
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def find_url_by_name(name):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM urls WHERE name=%s", (name,))
        return cur.fetchone()


def insert_url(name):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO urls (name, created_at)
            VALUES (%s, %s) RETURNING id""",
            (name, datetime.now()),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return new_id


def fetch_urls_with_last_check():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u.id,
                u.name,
                (
                    SELECT created_at FROM url_checks
                    WHERE url_id = u.id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) AS last_check,
                (
                    SELECT status_code FROM url_checks
                    WHERE url_id = u.id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) AS last_status
            FROM urls u
            ORDER BY u.id DESC
            """,
        )
        return cur.fetchall()


def fetch_url(id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, created_at FROM urls WHERE id=%s", (id,))
        url_item = cur.fetchone()
        if not url_item:
            return None, []
        cur.execute(
            """
            SELECT id, status_code, h1, title, description, created_at
            FROM url_checks
            WHERE url_id=%s
            ORDER BY created_at DESC
            """,
            (id,),
        )
        checks = cur.fetchall()
        return url_item, checks


def insert_url_check(url_id, status_code, h1, title, description):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO url_checks (
                url_id, status_code, h1, title, description, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (url_id, status_code, h1, title, description, datetime.now()),
        )
        conn.commit()
