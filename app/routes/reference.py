import sqlite3

from flask import Blueprint, jsonify, request, session

from app.database import get_db

reference_bp = Blueprint("reference", __name__)
TABLES = {
    "groups": "groups_ref",
    "teachers": "teachers",
    "subjects": "subjects",
    "classrooms": "classrooms",
}


def require_admin():
    if session.get("role") != "admin":
        return jsonify(error="Доступ разрешён только администратору."), 403
    return None


@reference_bp.get("/bootstrap")
def bootstrap():
    if "uid" not in session:
        return jsonify(error="Требуется авторизация."), 401
    db = get_db()
    return jsonify(
        groups=[dict(row) for row in db.execute("SELECT * FROM groups_ref ORDER BY name")],
        teachers=[dict(row) for row in db.execute("SELECT * FROM teachers ORDER BY full_name")],
        subjects=[dict(row) for row in db.execute("SELECT * FROM subjects ORDER BY name")],
        classrooms=[dict(row) for row in db.execute("SELECT * FROM classrooms ORDER BY name")],
    )


@reference_bp.post("/<name>")
def create_reference(name):
    error = require_admin()
    if error:
        return error

    if name not in TABLES:
        return jsonify(error="Неизвестный справочник."), 404

    data = request.get_json(silent=True) or {}
    db = get_db()

    try:
        if name == "groups":
            value = data.get("name", "").strip()
            if not value:
                return jsonify(error="Название группы не может быть пустым."), 400
            cursor = db.execute(
                "INSERT INTO groups_ref(name) VALUES(?)",
                (value,),
            )

        elif name == "teachers":
            full_name = data.get("full_name", "").strip()
            short_name = data.get("short_name", "").strip()
            if not full_name or not short_name:
                return jsonify(
                    error="ФИО и короткое имя преподавателя не могут быть пустыми."
                ), 400
            cursor = db.execute(
                "INSERT INTO teachers(full_name, short_name, color) VALUES(?, ?, ?)",
                (full_name, short_name, data.get("color", "#4f46e5")),
            )

        elif name == "subjects":
            value = data.get("name", "").strip()
            if not value:
                return jsonify(error="Название дисциплины не может быть пустым."), 400
            cursor = db.execute(
                "INSERT INTO subjects(name, color) VALUES(?, ?)",
                (value, data.get("color", "#6366f1")),
            )

        else:
            value = data.get("name", "").strip()
            if not value:
                return jsonify(error="Номер аудитории не может быть пустым."), 400
            cursor = db.execute(
                "INSERT INTO classrooms(name) VALUES(?)",
                (value,),
            )

        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(error="Такая запись уже существует."), 400
    except Exception as exc:
        db.rollback()
        return jsonify(error=f"Не удалось добавить запись: {exc}"), 400

    return jsonify(id=cursor.lastrowid), 201


@reference_bp.delete("/<name>/<int:item_id>")
def delete_reference(name, item_id):
    error = require_admin()
    if error:
        return error
    if name not in TABLES:
        return jsonify(error="Неизвестный справочник."), 404
    db = get_db()
    try:
        cursor = db.execute(f"DELETE FROM {TABLES[name]} WHERE id = ?", (item_id,))
        db.commit()
    except Exception as exc:
        return jsonify(error=f"Нельзя удалить запись: {exc}"), 400
    if cursor.rowcount == 0:
        return jsonify(error="Запись не найдена."), 404
    return jsonify(ok=True)
