from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from app.database import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    user = get_db().execute(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Неверный логин или пароль."), 401
    session["uid"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    return jsonify(username=user["username"], role=user["role"])


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@auth_bp.get("/me")
def me():
    if "uid" not in session:
        return jsonify(authenticated=False)
    return jsonify(
        authenticated=True,
        username=session.get("username"),
        role=session.get("role"),
    )
