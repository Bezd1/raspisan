from app.database import get_db


def list_lessons(week=None, group_id=None):
    query = """
        SELECT
            lessons.*,
            groups_ref.name AS group_name,
            teachers.full_name AS teacher_name,
            teachers.short_name AS teacher_short,
            subjects.name AS subject_name,
            subjects.color AS subject_color,
            classrooms.name AS classroom_name
        FROM lessons
        JOIN groups_ref ON groups_ref.id = lessons.group_id
        JOIN teachers ON teachers.id = lessons.teacher_id
        JOIN subjects ON subjects.id = lessons.subject_id
        LEFT JOIN classrooms ON classrooms.id = lessons.classroom_id
        WHERE 1 = 1
    """
    params = []

    if week in (1, 2):
        query += " AND lessons.week = ?"
        params.append(week)

    if group_id:
        query += " AND lessons.group_id = ?"
        params.append(group_id)

    query += " ORDER BY lessons.week, lessons.weekday, lessons.period, lessons.id"
    return [dict(row) for row in get_db().execute(query, params)]


def validate_lesson(data):
    required = {
        "week": "неделю",
        "weekday": "день недели",
        "period": "номер пары",
        "group_id": "группу",
        "teacher_id": "преподавателя",
        "subject_id": "дисциплину",
    }

    for field, title in required.items():
        value = data.get(field)
        if value is None or value == "" or (isinstance(value, str) and not value.strip()):
            return f"Не заполнено поле: {title}."

    try:
        week = int(data["week"])
        weekday = int(data["weekday"])
        period = int(data["period"])
        int(data["group_id"])
        int(data["teacher_id"])
        int(data["subject_id"])
    except (TypeError, ValueError):
        return "Некорректно заполнены числовые поля занятия."

    if week not in (1, 2):
        return "Неделя должна быть 1 или 2."
    if weekday not in range(1, 7):
        return "День недели должен быть от 1 до 6."
    if period not in range(1, 7):
        return "Номер пары должен быть от 1 до 6."

    lesson_type = str(data.get("lesson_type", "Лекция")).strip()
    if not lesson_type:
        return "Не заполнен тип занятия."

    return None


def conflict_message(data, exclude_id=None):
    query = """
        SELECT
            lessons.id,
            groups_ref.name AS group_name,
            teachers.full_name AS teacher_name,
            classrooms.name AS classroom_name
        FROM lessons
        JOIN groups_ref ON groups_ref.id = lessons.group_id
        JOIN teachers ON teachers.id = lessons.teacher_id
        LEFT JOIN classrooms ON classrooms.id = lessons.classroom_id
        WHERE lessons.week = ?
          AND lessons.weekday = ?
          AND lessons.period = ?
          AND (
              lessons.group_id = ?
              OR lessons.teacher_id = ?
              OR (
                  ? IS NOT NULL
                  AND lessons.classroom_id = ?
              )
          )
    """
    params = [
        int(data["week"]),
        int(data["weekday"]),
        int(data["period"]),
        int(data["group_id"]),
        int(data["teacher_id"]),
        data.get("classroom_id"),
        data.get("classroom_id"),
    ]

    if exclude_id:
        query += " AND lessons.id != ?"
        params.append(exclude_id)

    row = get_db().execute(query, params).fetchone()
    if not row:
        return None

    parts = []
    if row["group_name"]:
        parts.append(f"группа «{row['group_name']}»")
    if row["teacher_name"]:
        parts.append(f"преподаватель «{row['teacher_name']}»")
    if row["classroom_name"]:
        parts.append(f"аудитория «{row['classroom_name']}»")

    return "Конфликт: заняты " + ", ".join(parts) + "."


def _normalize(data):
    result = dict(data)
    result["week"] = int(result["week"])
    result["weekday"] = int(result["weekday"])
    result["period"] = int(result["period"])
    result["group_id"] = int(result["group_id"])
    result["teacher_id"] = int(result["teacher_id"])
    result["subject_id"] = int(result["subject_id"])
    result["classroom_id"] = (
        int(result["classroom_id"])
        if result.get("classroom_id") not in (None, "")
        else None
    )
    result["lesson_type"] = str(result.get("lesson_type", "Лекция")).strip()
    result["note"] = str(result.get("note", "")).strip()
    return result


def create_lesson(data):
    error = validate_lesson(data)
    if error:
        return None, error

    data = _normalize(data)

    db = get_db()
    assignment = db.execute(
        "SELECT 1 FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?",
        (data["teacher_id"], data["subject_id"]),
    ).fetchone()
    if assignment is None:
        return None, "Выбранная дисциплина не привязана к этому преподавателю."

    conflict = conflict_message(data)
    if conflict:
        return None, conflict

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO lessons (
            group_id, teacher_id, subject_id, classroom_id,
            weekday, period, week, lesson_type, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["group_id"],
            data["teacher_id"],
            data["subject_id"],
            data["classroom_id"],
            data["weekday"],
            data["period"],
            data["week"],
            data["lesson_type"],
            data["note"],
        ),
    )
    db.commit()
    return cursor.lastrowid, None


def update_lesson(lesson_id, data):
    if not get_db().execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,)).fetchone():
        return False, "Занятие не найдено."

    error = validate_lesson(data)
    if error:
        return False, error

    data = _normalize(data)

    db = get_db()
    assignment = db.execute(
        "SELECT 1 FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?",
        (data["teacher_id"], data["subject_id"]),
    ).fetchone()
    if assignment is None:
        return False, "Выбранная дисциплина не привязана к этому преподавателю."

    conflict = conflict_message(data, lesson_id)
    if conflict:
        return False, conflict

    get_db().execute(
        """
        UPDATE lessons
        SET group_id = ?, teacher_id = ?, subject_id = ?, classroom_id = ?,
            weekday = ?, period = ?, week = ?, lesson_type = ?, note = ?
        WHERE id = ?
        """,
        (
            data["group_id"],
            data["teacher_id"],
            data["subject_id"],
            data["classroom_id"],
            data["weekday"],
            data["period"],
            data["week"],
            data["lesson_type"],
            data["note"],
            lesson_id,
        ),
    )
    get_db().commit()
    return True, None


def delete_lesson(lesson_id):
    db = get_db()
    cursor = db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    db.commit()
    return cursor.rowcount > 0

def copy_week(source_week, target_week):
    """Copy all lessons from one week to another atomically.

    Existing lessons in the target week are treated as conflicts.
    If any conflict is found, nothing is copied.
    """
    if source_week not in (1, 2) or target_week not in (1, 2):
        return False, "Неделя должна быть 1 или 2.", 0

    if source_week == target_week:
        return False, "Нельзя копировать расписание на ту же неделю.", 0

    db = get_db()
    lessons = db.execute(
        """
        SELECT
            group_id, teacher_id, subject_id, classroom_id,
            weekday, period, lesson_type, note
        FROM lessons
        WHERE week = ?
        ORDER BY weekday, period, id
        """,
        (source_week,),
    ).fetchall()

    if not lessons:
        return False, f"В {source_week}-й неделе нет занятий для копирования.", 0

    conflicts = []
    for lesson in lessons:
        conflict = db.execute(
            """
            SELECT groups_ref.name AS group_name,
                   teachers.full_name AS teacher_name,
                   classrooms.name AS classroom_name
            FROM lessons
            JOIN groups_ref ON groups_ref.id = lessons.group_id
            JOIN teachers ON teachers.id = lessons.teacher_id
            LEFT JOIN classrooms ON classrooms.id = lessons.classroom_id
            WHERE lessons.week = ?
              AND lessons.weekday = ?
              AND lessons.period = ?
              AND (
                  lessons.group_id = ?
                  OR lessons.teacher_id = ?
                  OR (
                      ? IS NOT NULL
                      AND lessons.classroom_id = ?
                  )
              )
            LIMIT 1
            """,
            (
                target_week,
                lesson["weekday"],
                lesson["period"],
                lesson["group_id"],
                lesson["teacher_id"],
                lesson["classroom_id"],
                lesson["classroom_id"],
            ),
        ).fetchone()

        if conflict:
            conflicts.append(
                f"{lesson['weekday']} день, {lesson['period']} пара: "
                f"группа «{conflict['group_name']}»"
            )

    if conflicts:
        preview = "; ".join(conflicts[:3])
        if len(conflicts) > 3:
            preview += f"; и ещё {len(conflicts) - 3}"
        return False, f"Копирование отменено. В целевой неделе есть конфликты: {preview}.", 0

    try:
        db.execute("BEGIN")
        db.executemany(
            """
            INSERT INTO lessons (
                group_id, teacher_id, subject_id, classroom_id,
                weekday, period, week, lesson_type, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    lesson["group_id"],
                    lesson["teacher_id"],
                    lesson["subject_id"],
                    lesson["classroom_id"],
                    lesson["weekday"],
                    lesson["period"],
                    target_week,
                    lesson["lesson_type"],
                    lesson["note"],
                )
                for lesson in lessons
            ],
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return True, None, len(lessons)

