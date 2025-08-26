import os
from urllib.parse import urlparse

import validators
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from requests.exceptions import RequestException

from .database import (
    fetch_url,
    fetch_urls_with_last_check,
    find_url_by_name,
    insert_url,
    insert_url_check,
)
from .parser import fetch_html, parse_seo

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

MAX_URL_LENGTH = 255


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
        row = find_url_by_name(url_norm)
        if row:
            flash("Страница уже существует", "info")
            return redirect(url_for("show_url", id=row[0]))

        new_id = insert_url(url_norm)
        flash("Страница успешно добавлена", "success")
        return redirect(url_for("show_url", id=new_id))

    except Exception:
        flash("Ошибка при добавлении", "danger")
        return render_template("index.html", url=url), 500


# Список всех URL
@app.get("/urls")
def urls_index():
    urls_list = fetch_urls_with_last_check()
    return render_template("urls.html", urls=urls_list)


# Страница конкретного URL
@app.get("/urls/<int:id>")
def show_url(id):
    url_item, checks = fetch_url(id)
    if not url_item:
        flash("Страница не найдена", "danger")
        return redirect(url_for("urls_index"))

    return render_template("show_url.html", url=url_item, checks=checks)


# Проверка конкретного URL
@app.post("/urls/<int:id>/checks")
def create_check(id):
    url_item, _ = fetch_url(id)
    if not url_item:
        flash("Сайт не найден", "danger")
        return redirect(url_for("urls_index"))

    url = url_item[1]

    try:
        html, status_code = fetch_html(url, timeout=10)
        h1, title, description = parse_seo(html)

        insert_url_check(id, status_code, h1, title, description)
        flash("Страница успешно проверена", "success")

    except RequestException:
        flash("Произошла ошибка при проверке", "danger")

    return redirect(url_for("show_url", id=id))
