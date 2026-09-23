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


def admin_only():
    if session.get("role") != "admin":
        return jsonify({"error": "Только администратор может менять справочники."}), 403
    return None


@reference_bp.get("/bootstrap")
def bootstrap():
    if "user_id" not in session:
        return jsonify({"error": "Требуется авторизация."}), 401

    db = get_db()
    return jsonify(
        {
            "groups": [dict(row) for row in db.execute("SELECT * FROM groups_ref ORDER BY name")],
            "teachers": [dict(row) for row in db.execute("SELECT * FROM teachers ORDER BY full_name")],
            "subjects": [dict(row) for row in db.execute("SELECT * FROM subjects ORDER BY name")],
            "classrooms": [dict(row) for row in db.execute("SELECT * FROM classrooms ORDER BY name")],
            "teacher_subjects": [dict(row) for row in db.execute("SELECT teacher_id, subject_id FROM teacher_subjects")],
        }
    )


def _required_text(data, field, title):
    value = data.get(field)
    if value is None or not str(value).strip():
        raise ValueError(f"Не заполнено обязательное поле: {title}.")
    return str(value).strip()


def _create(name, data):
    db = get_db()

    if name == "teachers":
        full_name = _required_text(data, "full_name", "ФИО")
        short_name = "".join(part[0].upper() for part in full_name.split() if part)[:4]
        return db.execute(
            "INSERT INTO teachers (full_name, short_name, color) VALUES (?, ?, ?)",
            (full_name, short_name, str(data.get("color", "#4f46e5"))),
        ).lastrowid

    title = "название" if name in {"groups", "subjects"} else "номер аудитории"
    value = _required_text(data, "name", title)

    if name == "subjects":
        return db.execute(
            "INSERT INTO subjects (name, color) VALUES (?, ?)",
            (value, str(data.get("color", "#6366f1"))),
        ).lastrowid

    return db.execute(
        f"INSERT INTO {TABLES[name]} (name) VALUES (?)",
        (value,),
    ).lastrowid


@reference_bp.post("/references/<name>")
@reference_bp.post("/<name>")
def create_reference(name):
    error = admin_only()
    if error:
        return error

    if name not in TABLES:
        return jsonify({"error": "Неизвестный справочник."}), 404

    data = request.get_json(silent=True) or {}

    try:
        item_id = _create(name, data)
        get_db().commit()
        return jsonify({"id": item_id}), 201
    except ValueError as exc:
        get_db().rollback()
        return jsonify({"error": str(exc)}), 400
    except sqlite3.IntegrityError:
        get_db().rollback()
        return jsonify({"error": "Такая запись уже существует."}), 409


@reference_bp.put("/teachers/<int:teacher_id>/subjects")
def update_teacher_subjects(teacher_id):
    error = admin_only()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    subject_ids = data.get("subject_ids")
    if not isinstance(subject_ids, list):
        return jsonify({"error": "Список дисциплин указан неверно."}), 400

    db = get_db()
    teacher = db.execute("SELECT id FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    if teacher is None:
        return jsonify({"error": "Преподаватель не найден."}), 404

    try:
        normalized_ids = sorted({int(subject_id) for subject_id in subject_ids})
    except (TypeError, ValueError):
        return jsonify({"error": "Идентификаторы дисциплин указаны неверно."}), 400

    if normalized_ids:
        placeholders = ",".join("?" for _ in normalized_ids)
        count = db.execute(
            f"SELECT COUNT(*) FROM subjects WHERE id IN ({placeholders})",
            normalized_ids,
        ).fetchone()[0]
        if count != len(normalized_ids):
            return jsonify({"error": "Одна или несколько дисциплин не найдены."}), 400

    db.execute("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
    db.executemany(
        "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
        [(teacher_id, subject_id) for subject_id in normalized_ids],
    )
    db.commit()

    return jsonify({"ok": True, "subject_ids": normalized_ids})


@reference_bp.delete("/references/<name>/<int:item_id>")
@reference_bp.delete("/<name>/<int:item_id>")
def delete_reference(name, item_id):
    error = admin_only()
    if error:
        return error

    if name not in TABLES:
        return jsonify({"error": "Неизвестный справочник."}), 404

    db = get_db()
    try:
        cursor = db.execute(
            f"DELETE FROM {TABLES[name]} WHERE id = ?",
            (item_id,),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(
            {"error": "Нельзя удалить запись: она используется в расписании."}
        ), 409

    if cursor.rowcount == 0:
        return jsonify({"error": "Запись не найдена."}), 404

    return jsonify({"ok": True})
