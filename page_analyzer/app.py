import os
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
import requests
import validators
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from requests.exceptions import RequestException

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")

MAX_URL_LENGTH = 255  # Максимальная длина URL согласно стандарту


def get_conn():
    return psycopg2.connect(DATABASE_URL)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        if not url or not validators.url(url) or len(url) > MAX_URL_LENGTH:
            flash("Некорректный URL", "danger")
            return render_template("index.html", url=url)

        # Нормализация URL
        parsed = urlparse(url)
        url_norm = f"{parsed.scheme}://{parsed.netloc}"

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM urls WHERE name=%s", (url_norm,))
                    row = cur.fetchone()
                    if row:
                        flash("Страница уже существует", "info")
                        return redirect(url_for("show_url", id=row[0]))
                    cur.execute(
                        "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id",
                        (url_norm, datetime.now()),
                    )
                    new_id = cur.fetchone()[0]
                    flash("Страница успешно добавлена", "success")
                    return redirect(url_for("show_url", id=new_id))
        except Exception:
            flash("Ошибка при добавлении", "danger")
            return render_template("index.html", url=url)

    return render_template("index.html")


@app.route("/urls")
def urls():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id,
                       u.name,
                       MAX(c.created_at) AS last_check,
                       MAX(c.status_code) AS last_status
                FROM urls u
                LEFT JOIN url_checks c ON u.id = c.url_id
                GROUP BY u.id
                ORDER BY u.id DESC
            """)
            urls_list = cur.fetchall()
    return render_template("urls.html", urls=urls_list)


@app.route("/urls/<int:id>")
def show_url(id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM urls WHERE id=%s", (id,))
            url_item = cur.fetchone()
            if not url_item:
                flash("Страница не найдена", "danger")
                return redirect(url_for("urls"))

            cur.execute("""
                SELECT id, status_code, h1, title, description, created_at
                FROM url_checks
                WHERE url_id=%s
                ORDER BY created_at DESC
            """, (id,))
            checks = cur.fetchall()

    return render_template("show_url.html", url=url_item, checks=checks)


@app.route("/urls/<int:id>/checks", methods=["POST"])
def create_check(id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Получаем сам URL из базы
            cur.execute("SELECT name FROM urls WHERE id=%s", (id,))
            row = cur.fetchone()
            if not row:
                flash("Сайт не найден", "danger")
                return redirect(url_for("urls"))

            url = row[0]

            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                status_code = response.status_code

                # Сохраняем только если запрос успешный
                cur.execute(
                    """
                    INSERT INTO url_checks (url_id, status_code, created_at)
                    VALUES (%s, %s, %s)
                    """,
                    (id, status_code, datetime.now()),
                )
                conn.commit()
                flash("Страница успешно проверена", "success")

            except RequestException:
                flash("Произошла ошибка при проверке", "danger")

    return redirect(url_for("show_url", id=id))
