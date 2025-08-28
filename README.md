# Hexlet tests and linter status

[![Actions Status](https://github.com/WhiteA77/python-project-83/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/WhiteA77/python-project-83/actions)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=WhiteA77_python-project-83&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=WhiteA77_python-project-83)

## Название проекта

Анализатор веб-страниц

## Ссылка на деплой

<https://python-project-83-1-tglm.onrender.com>

## Структура проекта

Основной код приложения разделён на несколько модулей:

- `page_analyzer/app.py` содержит определение Flask-приложения и маршрутов
- `page_analyzer/database.py` включает функции работы с базой данных
- `page_analyzer/parser.py` отвечает за получение HTML и извлечение SEO-меток
- `page_analyzer/url_utils.py` предоставляет утилиты для валидации и нормализации URL

## Технологии

- Python 3.13 — основной язык разработки
- Flask — веб-фреймворк
- PostgreSQL — база данных
- Gunicorn — WSGI-сервер для продакшн-запуска
- uv — менеджер зависимостей и окружений
- Ruff — линтер и автоформаттер кода
- Pytest — тестирование

## Клонируем репозиторий

```bash

git clone https://github.com/WhiteA77/python-project-83.git

cd python-project-83

```

## Устанавливаем зависимости

```bash

make install

```

## Запускаем в режиме разработки

```bash

make dev

```

## Основные команды

- make install    # Установка зависимостей
- make dev        # Запуск в режиме разработки
- make start      # Запуск в продакшен-режиме
- make lint       # Проверка кода
- make test       # Запуск тестов
