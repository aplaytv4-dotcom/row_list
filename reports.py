import os
from collections import Counter, defaultdict
from datetime import datetime

from docxtpl import DocxTemplate, RichText


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DAILY_TEMPLATE = os.path.join(BASE_DIR, "daily_template.docx")
PERIOD_TEMPLATE = os.path.join(BASE_DIR, "period_template.docx")


def _autosave_filename(prefix):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return os.path.join(BASE_DIR, f"{prefix}_{stamp}.docx")


def _open_file(path):
    if hasattr(os, "startfile"):
        os.startfile(path)


def _render_template(template_path, context, prefix):
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Не найден шаблон: {template_path}")

    doc = DocxTemplate(template_path)
    doc.render(context)

    filename = _autosave_filename(prefix)
    doc.save(filename)

    _open_file(filename)
    return filename


def _format_date(date_text):
    return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d.%m.%Y")


def human_word(n):
    n = abs(n) % 100
    n1 = n % 10

    if 10 < n < 20:
        return "человек"
    if 1 < n1 < 5:
        return "человека"
    if n1 == 1:
        return "человек"
    return "человек"


def case_word(n):
    n = abs(n) % 100
    n1 = n % 10

    if 10 < n < 20:
        return "случаев"
    if 1 < n1 < 5:
        return "случая"
    if n1 == 1:
        return "случай"
    return "случаев"


# =====================================================
# ЕЖЕДНЕВНЫЙ ОТЧЁТ
# =====================================================

def generate_daily_report(
    rows,
    staff_total_with_vacancies=None,
    chief_name="Васин А.В."
):
    if staff_total_with_vacancies is None:
        staff_total_with_vacancies = len(rows)

    report_date = datetime.now().strftime("%d.%m.%Y")

    present_count = sum(1 for r in rows if r["status"] == "Присутствует")
    absent_rows = [r for r in rows if r["status"] != "Присутствует"]

    absent_count = len(absent_rows)

    reason_counter = Counter()
    respect_people = []

    for row in absent_rows:
        reason = row.get("reason", "").strip()
        name = row.get("name", "")
        comment = row.get("comment", "")

        if reason == "Уважительная причина":
            respect_people.append(
                f"{name} — {comment if comment else 'без уточнения'} — {report_date}"
            )
        else:
            reason_counter[reason] += 1

    absent_summary_parts = []
    for reason, count in reason_counter.items():
        absent_summary_parts.append(f"{reason} — {count} {human_word(count)}")

    absent_summary = ", ".join(absent_summary_parts) if absent_summary_parts else "-"

    respect_count = len(respect_people)
    respect_word = human_word(respect_count)

    respect_lines = RichText()

    if respect_people:
        for i, line in enumerate(respect_people, 1):
            respect_lines.add(f"{i}. {line}")
            if i < len(respect_people):
                respect_lines.add("\n")

        respect_lines.add("\n")
    else:
        respect_lines.add("-")

    context = {
        "report_date": report_date,
        "staff_total_with_vacancies": staff_total_with_vacancies,
        "staff_total_real": len(rows),
        "present_count": present_count,
        "present_word": human_word(present_count),
        "absent_count": absent_count,
        "absent_word": human_word(absent_count),
        "absent_summary": absent_summary,
        "respect_lines": respect_lines,
        "respect_count": respect_count,
        "respect_word": respect_word,
        "chief_name": chief_name,
        "current_date": report_date,
    }

    return _render_template(
        DAILY_TEMPLATE,
        context,
        "attendance_daily"
    )


# =====================================================
# ОТЧЁТ ЗА ПЕРИОД
# =====================================================

def generate_period_report(
    title,
    date_from,
    date_to,
    employees,
    attendance_rows,
    staff_total_with_vacancies=None,
    chief_name="Васин А.В."
):
    if staff_total_with_vacancies is None:
        staff_total_with_vacancies = len(employees)

    current_date = datetime.now().strftime("%d.%m.%Y")

    date_from_view = _format_date(date_from)
    date_to_view = _format_date(date_to)

    emp_names = {emp[0]: emp[4] for emp in employees}

    reason_counter = Counter()
    reason_people = defaultdict(list)

    respect_people = []
    absent_count = 0

    for emp_id, date, status, reason, comment in attendance_rows:
        if status == "Присутствует":
            continue

        absent_count += 1

        name = emp_names.get(emp_id, "")
        date_view = _format_date(date)

        reason = (reason or "").strip() or "Без причины"
        comment = (comment or "").strip()

        if reason == "Уважительная причина":
            respect_people.append({
                "name": name,
                "comment": comment if comment else "без уточнения",
                "date": date_view
            })
        else:
            reason_counter[reason] += 1
            reason_people[reason].append(f"{name} ({date_view})")

    absent_reason_lines = RichText()

    if reason_counter:
        items = list(reason_counter.items())
        for idx, (reason, count) in enumerate(items, start=1):
            people = ", ".join(reason_people[reason])
            line = f"{reason} — {count} {human_word(count)}: {people}"

            absent_reason_lines.add(line)
            if idx < len(items):
                absent_reason_lines.add("\n")
    else:
        absent_reason_lines.add("-")

    respect_lines = RichText()
    respect_count = len(respect_people)
    respect_word = human_word(respect_count)

    if respect_people:
        for i, item in enumerate(respect_people, 1):
            line = f"{i}. {item['name']} — {item['comment']} — {item['date']}"
            respect_lines.add(line)

            if i < len(respect_people):
                respect_lines.add("\n")

        respect_lines.add("\n")
    else:
        respect_lines.add("-")

    context = {
        "report_title": title,
        "date_from": date_from_view,
        "date_to": date_to_view,
        "current_date": current_date,
        "staff_total_with_vacancies": staff_total_with_vacancies,
        "staff_total_real": len(employees),
        "absent_count": absent_count,
        "absent_cases_word": case_word(absent_count),
        "absent_reason_lines": absent_reason_lines,
        "respect_lines": respect_lines,
        "respect_count": respect_count,
        "respect_word": respect_word,
        "chief_name": chief_name,
    }

    return _render_template(
        PERIOD_TEMPLATE,
        context,
        "attendance_period"
    )