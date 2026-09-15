from flask import Blueprint, jsonify, request, session

from app.services.lesson_service import create, delete, lessons, update

lessons_bp = Blueprint("lessons", __name__)


def require_login():
    if "uid" not in session:
        return jsonify(error="Требуется авторизация."), 401
    return None


@lessons_bp.get("/lessons")
def get_lessons():
    error = require_login()
    if error:
        return error
    week = request.args.get("week", type=int)
    group_id = request.args.get("group_id", type=int)
    return jsonify(lessons(week, group_id))


@lessons_bp.post("/lessons")
def add_lesson():
    error = require_login()
    if error:
        return error
    try:
        return jsonify(id=create(request.get_json(silent=True) or {})), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 409


@lessons_bp.put("/lessons/<int:lesson_id>")
def edit_lesson(lesson_id):
    error = require_login()
    if error:
        return error
    try:
        if not update(lesson_id, request.get_json(silent=True) or {}):
            return jsonify(error="Занятие не найдено."), 404
        return jsonify(ok=True)
    except ValueError as exc:
        return jsonify(error=str(exc)), 409


@lessons_bp.delete("/lessons/<int:lesson_id>")
def remove_lesson(lesson_id):
    error = require_login()
    if error:
        return error
    if not delete(lesson_id):
        return jsonify(error="Занятие не найдено."), 404
    return jsonify(ok=True)
