import os
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
import requests
import validators
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from requests.exceptions import RequestException

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")
MAX_URL_LENGTH = 255


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# Главная
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return redirect(url_for("urls_create"), code=307)
    return render_template("index.html")


# Создание нового URL
@app.post("/urls")
def urls_create():
    url = request.form.get("url", "").strip()

    # Валидация
    if not url or not validators.url(url) or len(url) > MAX_URL_LENGTH:
        flash("Некорректный URL", "danger")
        return render_template("index.html", url=url), 422

    # Нормализация URL: схема + хост
    parsed = urlparse(url)
    url_norm = f"{parsed.scheme}://{parsed.netloc}"

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM urls WHERE name=%s", (url_norm,))
            row = cur.fetchone()
            if row:
                flash("Страница уже существует", "info")
                return redirect(url_for("show_url", id=row[0]))

            # Создание
            cur.execute(
                "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id",
                (url_norm, datetime.now()),
            )
            new_id = cur.fetchone()[0]
            flash("Страница успешно добавлена", "success")
            return redirect(url_for("show_url", id=new_id))

    except Exception:
        flash("Ошибка при добавлении", "danger")
        return render_template("index.html", url=url), 500


# Список всех URL
@app.get("/urls")
def urls_index():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u.id,
                u.name,
                lc.created_at AS last_check,
                lc.status_code AS last_status
            FROM urls u
            LEFT JOIN LATERAL (
                SELECT status_code, created_at
                FROM url_checks
                WHERE url_id = u.id
                ORDER BY created_at DESC
                LIMIT 1
            ) AS lc ON true
            ORDER BY u.id DESC
            """
        )
        urls_list = cur.fetchall()
    return render_template("urls.html", urls=urls_list)


# Страница конкретного URL
@app.get("/urls/<int:id>")
def show_url(id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, created_at FROM urls WHERE id=%s", (id,))
        url_item = cur.fetchone()
        if not url_item:
            flash("Страница не найдена", "danger")
            return redirect(url_for("urls_index"))

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

    return render_template("show_url.html", url=url_item, checks=checks)


# Проверка конкретного URL
@app.post("/urls/<int:id>/checks")
def create_check(id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT name FROM urls WHERE id=%s", (id,))
        row = cur.fetchone()
        if not row:
            flash("Сайт не найден", "danger")
            return redirect(url_for("urls_index"))

        url = row[0]

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            status_code = response.status_code
            html = response.text

            # Парсинг SEO-полей
            soup = BeautifulSoup(html, "html.parser")

            h1 = soup.h1.string.strip() if soup.h1 and soup.h1.string else None
            title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else None
            )

            description_tag = soup.find("meta", attrs={"name": "description"})
            description = (
                description_tag.get("content", "").strip()
                if description_tag and description_tag.get("content")
                else None
            )

            # Сохраняем успешную проверку
            cur.execute(
                """
                INSERT INTO url_checks (
                    url_id, status_code, h1, title, description, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (id, status_code, h1, title, description, datetime.now()),
            )
            conn.commit()
            flash("Страница успешно проверена", "success")

        except RequestException:
            flash("Произошла ошибка при проверке", "danger")

    return redirect(url_for("show_url", id=id))
