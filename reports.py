import os
from collections import Counter, defaultdict
from datetime import datetime

from docxtpl import DocxTemplate


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DAILY_TEMPLATE = os.path.join(BASE_DIR, "daily_template.docx")
PERIOD_TEMPLATE = os.path.join(BASE_DIR, "period_template.docx")

DATE_FORMAT = "%d.%m.%Y"


def _autosave_filename(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return os.path.join(BASE_DIR, f"{prefix}_{stamp}.docx")


def _open_file(path: str) -> None:
    if hasattr(os, "startfile"):
        os.startfile(path)


def _render_template(template_path: str, context: dict, output_prefix: str) -> str:
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Не найден шаблон: {template_path}")

    doc = DocxTemplate(template_path)
    doc.render(context)

    filename = _autosave_filename(output_prefix)
    doc.save(filename)
    _open_file(filename)
    return filename


def _format_dates(dates) -> str:
    unique_dates = []
    for d in dates:
        if d not in unique_dates:
            unique_dates.append(d)
    return ", ".join(unique_dates)


def _plural(count: int, form1: str, form2: str, form5: str) -> str:
    n = abs(count) % 100
    n1 = n % 10

    if 11 <= n <= 19:
        return form5
    if n1 == 1:
        return form1
    if 2 <= n1 <= 4:
        return form2
    return form5


def _people_text(count: int) -> str:
    return f"{count} {_plural(count, 'человек', 'человека', 'человек')}"


def _cases_text(count: int) -> str:
    return f"{count} {_plural(count, 'случай', 'случая', 'случаев')}"


def _build_absent_summary(reason_counter: Counter) -> str:
    if not reason_counter:
        return "-"

    parts = []
    for reason, count in reason_counter.items():
        parts.append(f"{reason}-({_people_text(count)})")
    return ", ".join(parts)


def generate_daily_report(
    rows,
    staff_total_with_vacancies=None,
    chief_name="Васин А.В.",
):
    if staff_total_with_vacancies is None:
        staff_total_with_vacancies = len(rows)

    report_date = datetime.now().strftime(DATE_FORMAT)
    current_date = datetime.now().strftime(DATE_FORMAT)

    staff_total_real = len(rows)
    present_count = sum(1 for row in rows if row["status"] == "Присутствует")
    absent_rows = [row for row in rows if row["status"] == "Отсутствует"]
    absent_count = len(absent_rows)

    reason_counter = Counter()
    askoff_people = []

    for row in absent_rows:
        reason = (row.get("reason") or "").strip()
        comment = (row.get("comment") or "").strip()
        name = (row.get("name") or "").strip()

        if reason:
            reason_counter[reason] += 1
        else:
            reason_counter["Без причины"] += 1

        if reason == "Отпросился":
            askoff_people.append(
                {
                    "name": name,
                    "comment": comment if comment else "без уточнения",
                    "date": report_date,
                }
            )

    absent_summary = _build_absent_summary(reason_counter)

    if askoff_people:
        askoff_lines = "\n".join(
            f"{index}. {item['name']} - {item['comment']} - {item['date']}"
            for index, item in enumerate(askoff_people, start=1)
        )
    else:
        askoff_lines = "-"

    askoff_count = len(askoff_people)

    context = {
        "report_date": report_date,
        "current_date": current_date,
        "staff_total_with_vacancies": staff_total_with_vacancies,
        "staff_total_real": staff_total_real,
        "present_count": present_count,
        "present_count_text": _people_text(present_count),
        "absent_count": absent_count,
        "absent_count_text": _people_text(absent_count),
        "absent_summary": absent_summary,
        "askoff_count": askoff_count,
        "askoff_count_text": _people_text(askoff_count),
        "askoff_lines": askoff_lines,
        "chief_name": chief_name,
    }

    return _render_template(DAILY_TEMPLATE, context, "attendance_daily")


def generate_period_report(
    title: str,
    date_from: str,
    date_to: str,
    employees,
    attendance_rows,
    staff_total_with_vacancies=None,
    chief_name="Васин А.В.",
):
    if staff_total_with_vacancies is None:
        staff_total_with_vacancies = len(employees)

    current_date = datetime.now().strftime(DATE_FORMAT)
    date_from_view = datetime.strptime(date_from, "%Y-%m-%d").strftime(DATE_FORMAT)
    date_to_view = datetime.strptime(date_to, "%Y-%m-%d").strftime(DATE_FORMAT)

    staff_total_real = len(employees)

    emp_name_by_id = {}
    for emp_id, department, position, rank, name in employees:
        emp_name_by_id[emp_id] = name

    reason_counter = Counter()
    reason_people = defaultdict(list)
    askoff_map = defaultdict(list)

    absent_count = 0

    for emp_id, date, status, reason, comment in attendance_rows:
        if emp_id not in emp_name_by_id:
            continue

        if status != "Отсутствует":
            continue

        absent_count += 1

        name = emp_name_by_id[emp_id]
        reason_text = (reason or "").strip() or "Без причины"
        comment_text = (comment or "").strip()
        date_view = datetime.strptime(date, "%Y-%m-%d").strftime(DATE_FORMAT)

        reason_counter[reason_text] += 1
        reason_people[reason_text].append(name)

        if reason_text == "Отпросился":
            askoff_reason = comment_text if comment_text else "без уточнения"
            askoff_map[(name, askoff_reason)].append(date_view)

    absent_summary = _build_absent_summary(reason_counter)

    if reason_counter:
        lines = []
        for reason, count in reason_counter.items():
            people = []
            for fio in reason_people[reason]:
                if fio not in people:
                    people.append(fio)

            people_text = ", ".join(people) if people else "-"
            lines.append(f"{reason}-({_people_text(count)}) {people_text}")

        absent_reason_lines = "\n".join(lines)
    else:
        absent_reason_lines = "-"

    if askoff_map:
        items = sorted(askoff_map.items(), key=lambda x: (x[0][0], x[0][1]))
        askoff_lines = "\n".join(
            f"{index}. {employee_name} - {askoff_reason} - {_format_dates(dates)}"
            for index, ((employee_name, askoff_reason), dates) in enumerate(items, start=1)
        )
    else:
        askoff_lines = "-"

    askoff_count = len({name for (name, _reason) in askoff_map.keys()})

    context = {
        "report_title": title,
        "date_from": date_from_view,
        "date_to": date_to_view,
        "current_date": current_date,
        "staff_total_with_vacancies": staff_total_with_vacancies,
        "staff_total_real": staff_total_real,
        "absent_count": absent_count,
        "absent_count_text": _cases_text(absent_count),
        "absent_summary": absent_summary,
        "absent_reason_lines": absent_reason_lines,
        "askoff_count": askoff_count,
        "askoff_count_text": _people_text(askoff_count),
        "askoff_lines": askoff_lines,
        "chief_name": chief_name,
    }

    return _render_template(PERIOD_TEMPLATE, context, "attendance_period")