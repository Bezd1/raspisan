import os
import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'teacher'
);

CREATE TABLE IF NOT EXISTS groups_ref (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#4f46e5'
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#6366f1'
);

CREATE TABLE IF NOT EXISTS classrooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS teacher_subjects (
    teacher_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    PRIMARY KEY (teacher_id, subject_id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    classroom_id INTEGER,
    weekday INTEGER NOT NULL,
    period INTEGER NOT NULL,
    week INTEGER NOT NULL DEFAULT 1,
    lesson_type TEXT NOT NULL DEFAULT 'Лекция',
    note TEXT DEFAULT '',
    FOREIGN KEY (group_id) REFERENCES groups_ref(id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id)
);
"""


def _columns(db, table_name):
    return {
        row[1]
        for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _migrate_users(db):
    columns = _columns(db, "users")
    if not columns:
        return

    # Старые версии проекта хранили пароль в колонке password.
    # Переносим такие данные в password_hash. Если пароль был обычным текстом,
    # seed_service позже заменит демо-учётки на безопасные хэши.
    if "password_hash" not in columns and "password" in columns:
        db.execute("ALTER TABLE users RENAME TO users_old")
        db.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'teacher'
            )
            """
        )
        old_columns = _columns(db, "users_old")
        role_expression = "role" if "role" in old_columns else "'teacher'"
        db.execute(
            f"""
            INSERT INTO users (id, username, password_hash, role)
            SELECT id, username, password, {role_expression}
            FROM users_old
            """
        )
        db.execute("DROP TABLE users_old")


def _migrate_lessons(db):
    columns = _columns(db, "lessons")
    if not columns:
        return

    # Старые версии использовали day/pair_number/notes.
    if "weekday" not in columns and "day" in columns:
        db.execute("ALTER TABLE lessons RENAME TO lessons_old")
        db.execute(
            """
            CREATE TABLE lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                teacher_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                classroom_id INTEGER,
                weekday INTEGER NOT NULL,
                period INTEGER NOT NULL,
                week INTEGER NOT NULL DEFAULT 1,
                lesson_type TEXT NOT NULL DEFAULT 'Лекция',
                note TEXT DEFAULT '',
                FOREIGN KEY (group_id) REFERENCES groups_ref(id),
                FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id),
                FOREIGN KEY (classroom_id) REFERENCES classrooms(id)
            )
            """
        )
        old_columns = _columns(db, "lessons_old")
        note_column = "notes" if "notes" in old_columns else "''"
        lesson_type_column = "lesson_type" if "lesson_type" in old_columns else "'Лекция'"
        db.execute(
            f"""
            INSERT INTO lessons (
                id, group_id, teacher_id, subject_id, classroom_id,
                weekday, period, week, lesson_type, note
            )
            SELECT
                id, group_id, teacher_id, subject_id, classroom_id,
                day, pair_number, week, {lesson_type_column}, {note_column}
            FROM lessons_old
            """
        )
        db.execute("DROP TABLE lessons_old")


def init_db(app):
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        _migrate_users(db)
        _migrate_lessons(db)
        db.commit()

    app.teardown_appcontext(close_db)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
