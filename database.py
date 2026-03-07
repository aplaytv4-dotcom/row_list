import os
import sqlite3
from typing import Dict, List, Tuple


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
EMPLOYEES_FILE = os.path.join(BASE_DIR, "employees.txt")
REASONS_FILE = os.path.join(BASE_DIR, "reasons.txt")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sort_order INTEGER,
            department TEXT NOT NULL,
            position TEXT NOT NULL,
            rank TEXT NOT NULL,
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(department, position, rank, name)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            FOREIGN KEY(emp_id) REFERENCES employees(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_emp_date
        ON attendance(emp_id, date)
        """
    )

    conn.commit()
    conn.close()


def read_text_lines(file_path: str) -> List[str]:
    if not os.path.exists(file_path):
        return []

    lines: List[str] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            value = line.strip()
            if value:
                lines.append(value)
    return lines


def load_reasons() -> List[str]:
    reasons = read_text_lines(REASONS_FILE)
    if not reasons:
        reasons = [
            "Больничный",
            "Отпуск",
            "Командировка",
            "Дежурство",
            "Отпросился",
        ]
    return reasons


def sync_employees_from_file() -> int:
    """
    Синхронизирует сотрудников из employees.txt в таблицу employees.
    Порядок строк сохраняется через sort_order.
    Старые записи attendance не удаляются.
    Сотрудники, которых больше нет в файле, помечаются is_active = 0.
    """
    if not os.path.exists(EMPLOYEES_FILE):
        return 0

    conn = connect()
    cur = conn.cursor()

    processed = 0
    current_keys = []

    with open(EMPLOYEES_FILE, "r", encoding="utf-8") as f:
        for index, line in enumerate(f, start=1):
            parts = [p.strip() for p in line.strip().split(";")]
            if len(parts) != 4:
                continue

            department, position, rank, name = parts
            key = (department, position, rank, name)
            current_keys.append(key)

            cur.execute(
                """
                SELECT id
                FROM employees
                WHERE department = ? AND position = ? AND rank = ? AND name = ?
                """,
                key,
            )
            row = cur.fetchone()

            if row:
                cur.execute(
                    """
                    UPDATE employees
                    SET sort_order = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (index, row[0]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO employees(sort_order, department, position, rank, name, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (index, department, position, rank, name),
                )

            processed += 1

    # Помечаем отсутствующих в текущем файле как неактивных
    cur.execute(
        """
        SELECT id, department, position, rank, name
        FROM employees
        """
    )
    all_db_rows = cur.fetchall()

    for emp_id, department, position, rank, name in all_db_rows:
        key = (department, position, rank, name)
        if key not in current_keys:
            cur.execute(
                """
                UPDATE employees
                SET is_active = 0
                WHERE id = ?
                """,
                (emp_id,),
            )

    conn.commit()
    conn.close()
    return processed


def get_employees() -> List[Tuple[int, str, str, str, str]]:
    """
    Возвращает активных сотрудников для интерфейса.
    Вакантные места тоже возвращаются, если они есть в employees.txt.
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, department, position, rank, name
        FROM employees
        WHERE is_active = 1
        ORDER BY sort_order, id
        """
    )
    rows = cur.fetchall()

    conn.close()
    return rows


def get_staff_total() -> int:
    """
    Количество реальных активных сотрудников без вакансий.
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM employees
        WHERE is_active = 1
          AND UPPER(name) NOT LIKE 'ВАКАНТ%'
        """
    )
    total = cur.fetchone()[0]

    conn.close()
    return total


def save_status(
    emp_id: int,
    date: str,
    status: str,
    reason: str = "",
    comment: str = "",
) -> None:
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO attendance(emp_id, date, status, reason, comment)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(emp_id, date)
        DO UPDATE SET
            status = excluded.status,
            reason = excluded.reason,
            comment = excluded.comment
        """,
        (emp_id, date, status, reason, comment),
    )

    conn.commit()
    conn.close()


def load_today_status(date: str) -> Dict[int, Dict[str, str]]:
    """
    Загружает статусы за указанный день:
    {
        emp_id: {
            "status": "...",
            "reason": "...",
            "comment": "..."
        }
    }
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT emp_id, status, COALESCE(reason, ''), COALESCE(comment, '')
        FROM attendance
        WHERE date = ?
        """,
        (date,),
    )
    rows = cur.fetchall()

    conn.close()

    result: Dict[int, Dict[str, str]] = {}
    for emp_id, status, reason, comment in rows:
        result[emp_id] = {
            "status": status,
            "reason": reason,
            "comment": comment,
        }

    return result


def get_attendance_rows(date_from: str, date_to: str):
    """
    Возвращает все записи attendance по активным реальным сотрудникам за период.
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.emp_id,
            a.date,
            a.status,
            COALESCE(a.reason, ''),
            COALESCE(a.comment, '')
        FROM attendance a
        JOIN employees e ON e.id = a.emp_id
        WHERE a.date BETWEEN ? AND ?
          AND e.is_active = 1
          AND UPPER(e.name) NOT LIKE 'ВАКАНТ%'
        ORDER BY a.date, a.emp_id
        """,
        (date_from, date_to),
    )
    rows = cur.fetchall()

    conn.close()
    return rows


def get_month_employee_stats(date_from: str, date_to: str):
    """
    Возвращает:
    employees:
        [(id, department, position, rank, name), ...]
    attendance_rows:
        [(emp_id, date, status, reason, comment), ...]
    Только по активным реальным сотрудникам, без вакансий.
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, department, position, rank, name
        FROM employees
        WHERE is_active = 1
          AND UPPER(name) NOT LIKE 'ВАКАНТ%'
        ORDER BY sort_order, id
        """
    )
    employees = cur.fetchall()

    cur.execute(
        """
        SELECT a.emp_id, a.date, a.status, COALESCE(a.reason, ''), COALESCE(a.comment, '')
        FROM attendance a
        JOIN employees e ON e.id = a.emp_id
        WHERE a.date BETWEEN ? AND ?
          AND e.is_active = 1
          AND UPPER(e.name) NOT LIKE 'ВАКАНТ%'
        ORDER BY a.date, a.emp_id
        """,
        (date_from, date_to),
    )
    attendance_rows = cur.fetchall()

    conn.close()
    return employees, attendance_rows


def employees_exist() -> bool:
    """
    Необязательная вспомогательная функция.
    """
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM employees WHERE is_active = 1")
    count = cur.fetchone()[0]

    conn.close()
    return count > 0