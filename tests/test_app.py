from werkzeug.security import generate_password_hash

from app import create_app
from app.database import get_db


def test_health():
    app = create_app()
    client = app.test_client()
    assert client.get("/health").status_code == 200


def test_login():
    app = create_app()
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin"), "admin"),
        )
        db.commit()

    client = app.test_client()
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"
