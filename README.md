# Schedule App — готовая версия

Веб-приложение для визуального формирования учебного расписания.

## Стек
Python 3 + Flask + SQLite + HTML5 + CSS3 + Vanilla JavaScript.

## ВАЖНО
Открывай в VS Code папку проекта, в которой одновременно находятся:
- `run.py`
- `app`
- `templates`
- `static`

Структура должна выглядеть так:

schedule_app_ready/
  run.py
  requirements.txt
  app/
  templates/
    index.html
  static/
    style.css
    app.js

## Запуск

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

Затем открой:

http://127.0.0.1:5000/

Логин: `admin`
Пароль: `admin`

Также доступны `teacher/teacher` и `student/student`.

## Исправления

В этой версии:
- добавлен маршрут `/`;
- Flask получает абсолютный путь к `templates`;
- Flask получает абсолютный путь к `static`;
- seed-данные создаются внутри `app.app_context()`;
- SQLite создаётся автоматически;
- добавлена проверка `/health`.

Ошибка `TemplateNotFound: index.html`, возникшая в предыдущей версии, исправлена архитектурно: Flask больше не зависит от текущей рабочей директории.
