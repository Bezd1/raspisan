from app.database import get_db


LESSON_QUERY = """
SELECT
    l.*,
    g.name AS group_name,
    t.full_name AS teacher_name,
    t.short_name AS teacher_short,
    t.color AS teacher_color,
    s.name AS subject_name,
    s.color AS subject_color,
    c.name AS classroom_name
FROM lessons AS l
JOIN groups_ref AS g ON g.id = l.group_id
JOIN teachers AS t ON t.id = l.teacher_id
JOIN subjects AS s ON s.id = l.subject_id
LEFT JOIN classrooms AS c ON c.id = l.classroom_id
"""


def lessons(week=None, group_id=None):
    query = LESSON_QUERY + " WHERE 1 = 1"
    params = []
    if week in (1, 2):
        query += " AND l.week = ?"
        params.append(week)
    if group_id:
        query += " AND l.group_id = ?"
        params.append(group_id)
    query += " ORDER BY l.week, l.weekday, l.period, l.id"
    return [dict(row) for row in get_db().execute(query, params)]


def conflict(data, exclude=None):
    query = """
    SELECT
        l.id,
        g.name AS group_name,
        t.full_name AS teacher_name,
        c.name AS classroom_name
    FROM lessons AS l
    JOIN groups_ref AS g ON g.id = l.group_id
    JOIN teachers AS t ON t.id = l.teacher_id
    LEFT JOIN classrooms AS c ON c.id = l.classroom_id
    WHERE l.week = ?
      AND l.weekday = ?
      AND l.period = ?
      AND (
          l.group_id = ?
          OR l.teacher_id = ?
          OR (l.classroom_id IS NOT NULL AND l.classroom_id = ?)
      )
    """
    params = [
        data["week"], data["weekday"], data["period"],
        data["group_id"], data["teacher_id"], data.get("classroom_id"),
    ]
    if exclude is not None:
        query += " AND l.id != ?"
        params.append(exclude)
    return get_db().execute(query, params).fetchone()


def _validate(data):
    required = ["group_id", "teacher_id", "subject_id", "weekday", "period", "week"]
    missing = [
        field
        for field in required
        if field not in data or data[field] in (None, "")
    ]
    if missing:
        raise ValueError("Не заполнены обязательные поля: " + ", ".join(missing))

    if data["week"] not in (1, 2):
        raise ValueError("Неделя должна быть 1 или 2.")
    if not 1 <= data["weekday"] <= 6:
        raise ValueError("День недели должен быть от 1 до 6.")
    if not 1 <= data["period"] <= 6:
        raise ValueError("Номер пары должен быть от 1 до 6.")


def create(data):
    _validate(data)
    found = conflict(data)
    if found:
        raise ValueError(_conflict_message(found))

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO lessons (
            group_id, teacher_id, subject_id, classroom_id,
            weekday, period, week, lesson_type, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["group_id"], data["teacher_id"], data["subject_id"],
            data.get("classroom_id"), data["weekday"], data["period"],
            data.get("week", 1), data.get("lesson_type", "Лекция"),
            data.get("note", ""),
        ),
    )
    db.commit()
    return cursor.lastrowid


def update(lesson_id, data):
    _validate(data)
    found = conflict(data, lesson_id)
    if found:
        raise ValueError(_conflict_message(found))

    db = get_db()
    cursor = db.execute(
        """
        UPDATE lessons
        SET group_id = ?, teacher_id = ?, subject_id = ?, classroom_id = ?,
            weekday = ?, period = ?, week = ?, lesson_type = ?, note = ?
        WHERE id = ?
        """,
        (
            data["group_id"], data["teacher_id"], data["subject_id"],
            data.get("classroom_id"), data["weekday"], data["period"],
            data.get("week", 1), data.get("lesson_type", "Лекция"),
            data.get("note", ""), lesson_id,
        ),
    )
    db.commit()
    return cursor.rowcount > 0


def delete(lesson_id):
    db = get_db()
    cursor = db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    db.commit()
    return cursor.rowcount > 0


def _conflict_message(row):
    parts = []
    if row["group_name"]:
        parts.append(f"группа «{row['group_name']}»")
    if row["teacher_name"]:
        parts.append(f"преподаватель «{row['teacher_name']}»")
    if row["classroom_name"]:
        parts.append(f"аудитория «{row['classroom_name']}»")
    return "Конфликт: заняты " + ", ".join(parts) + "."
