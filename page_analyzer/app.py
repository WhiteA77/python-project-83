import os
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
import requests
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

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS url_checks (
                    id SERIAL PRIMARY KEY,
                    url_id INTEGER REFERENCES urls(id) ON DELETE CASCADE,
                    status_code INTEGER,
                    h1 VARCHAR(255),
                    title VARCHAR(255),
                    description TEXT,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()

def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        if not url or not validate_url(url) or len(url) > MAX_URL_LENGTH:
            flash("Некорректный URL", "danger")
            return render_template("index.html", url=url)

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
                SELECT u.id, u.name, 
                       MAX(c.created_at) AS last_check,
                       c.status_code
                FROM urls u
                LEFT JOIN url_checks c ON u.id = c.url_id
                GROUP BY u.id, c.status_code
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
            cur.execute("SELECT name FROM urls WHERE id=%s", (id,))
            row = cur.fetchone()
            if not row:
                flash("Сайт не найден", "danger")
                return redirect(url_for("urls"))

            url = row[0]

            try:
                response = requests.get(url, timeout=10)
                status_code = response.status_code
                html = response.text

                soup = BeautifulSoup(html, "html.parser")
                
                h1 = soup.h1.get_text().strip() if soup.h1 else None
                title = soup.title.get_text().strip() if soup.title else None
                
                description_tag = soup.find("meta", attrs={"name": "description"})
                description = description_tag["content"].strip() if description_tag and description_tag.get("content") else None

                cur.execute(
                    """
                    INSERT INTO url_checks (url_id, status_code, h1, title, description, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (id, status_code, h1, title, description, datetime.now()),
                )
                conn.commit()
                flash("Страница успешно проверена", "success")

            except RequestException:
                flash("Произошла ошибка при проверке", "danger")

    return redirect(url_for("show_url", id=id))