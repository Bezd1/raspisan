from werkzeug.security import generate_password_hash

from app.database import get_db


DEMO_USERS = [
    ("admin", "admin", "admin"),
    ("teacher", "teacher", "teacher"),
]


def _ensure_demo_users(db):
    for username, password, role in DEMO_USERS:
        user = db.execute(
            "SELECT id, password_hash, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        password_hash = generate_password_hash(password)
        if user is None:
            db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
        else:
            # Исправляет старые версии, где пароль был сохранён обычным текстом.
            if not user["password_hash"].startswith(("scrypt:", "pbkdf2:")):
                db.execute(
                    "UPDATE users SET password_hash = ?, role = ? WHERE id = ?",
                    (password_hash, role, user["id"]),
                )

    # Учётная запись студента больше не используется.
    db.execute("DELETE FROM users WHERE username = 'student'")


def seed_demo_data():
    db = get_db()
    _ensure_demo_users(db)

    for name in ["П-21", "П-22", "П-23", "ИС-21"]:
        db.execute("INSERT OR IGNORE INTO groups_ref (name) VALUES (?)", (name,))

    teachers = [
        ("Иванов Сергей Владимирович", "ИВ"),
        ("Петрова Анна Игоревна", "ПА"),
        ("Сидоров Дмитрий Андреевич", "СД"),
        ("Морозова Елена Викторовна", "МЕ"),
    ]
    for full_name, short_name in teachers:
        db.execute(
            """
            INSERT INTO teachers (full_name, short_name)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM teachers WHERE full_name = ?
            )
            """,
            (full_name, short_name, full_name),
        )

    subjects = [
        ("Информатика", "#5b6cff"),
        ("ОАП", "#0ea5e9"),
        ("Программирование", "#8b5cf6"),
        ("Математика", "#f59e0b"),
        ("Физика", "#10b981"),
        ("Базы данных", "#ef4444"),
    ]
    for name, color in subjects:
        db.execute(
            "INSERT OR IGNORE INTO subjects (name, color) VALUES (?, ?)",
            (name, color),
        )

    for room in ["204", "305", "312", "401"]:
        db.execute("INSERT OR IGNORE INTO classrooms (name) VALUES (?)", (room,))

    db.commit()

    if db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] > 0:
        return

    groups = {
        row["name"]: row["id"]
        for row in db.execute("SELECT id, name FROM groups_ref")
    }
    teachers_by_short = {
        row["short_name"]: row["id"]
        for row in db.execute("SELECT id, short_name FROM teachers")
    }
    subjects_by_name = {
        row["name"]: row["id"]
        for row in db.execute("SELECT id, name FROM subjects")
    }
    rooms = {
        row["name"]: row["id"]
        for row in db.execute("SELECT id, name FROM classrooms")
    }

    demo_lessons = [
        (1, 1, 1, "П-21", "ИВ", "Информатика", "204"),
        (1, 1, 2, "П-21", "СД", "Программирование", "305"),
        (1, 2, 1, "П-22", "ПА", "Математика", "312"),
        (1, 3, 2, "П-23", "МЕ", "Физика", "401"),
        (2, 1, 1, "ИС-21", "ИВ", "Базы данных", "204"),
        (2, 2, 3, "П-22", "СД", "ОАП", "305"),
    ]

    for week, weekday, period, group, teacher, subject, room in demo_lessons:
        db.execute(
            """
            INSERT INTO lessons (
                week, weekday, period, group_id, teacher_id,
                subject_id, classroom_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                week,
                weekday,
                period,
                groups[group],
                teachers_by_short[teacher],
                subjects_by_name[subject],
                rooms[room],
            ),
        )

    db.commit()
