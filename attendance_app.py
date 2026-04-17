import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import os
import sys
import subprocess
import platform
import sqlite3

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class AttendanceApp:
    """Приложение для учета присутствия сотрудников."""

    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("Учет присутствия 3.0")
        self.app.geometry("1200x650")

        self.base_path = self.get_base_path()
        self.reports_path = self.get_reports_path()
        self.history_path = self.get_resource_path("attendance_history.db")
        self.initialize_database()

        self.employees = self.load_employees()
        self.reasons = self.load_reasons()
        self.rows = []

        self.setup_ui()

    def get_resource_path(self, filename):
        """Получить путь к файлу рядом с приложением."""
        if getattr(sys, "frozen", False):
            return os.path.join(os.path.dirname(sys.executable), filename)
        return os.path.join(self.base_path, filename)

    def get_report_path(self, filename):
        """Получить путь к файлу отчета."""
        return os.path.join(self.reports_path, filename)

    def get_base_path(self):
        """Получить базовый путь приложения."""
        if getattr(sys, "frozen", False):
            return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.dirname(__file__)

    def get_reports_path(self):
        """Получить путь к папке отчетов."""
        reports_dir = os.path.join(
            os.path.dirname(self.get_resource_path("attendance_app.py")),
            "Отчеты"
        )
        os.makedirs(reports_dir, exist_ok=True)
        return reports_dir

    def connect_db(self):
        """Открыть соединение с SQLite."""
        connection = sqlite3.connect(self.history_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_database(self):
        """Создать пустую базу данных истории."""
        try:
            with self.connect_db() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS attendance_records (
                        record_date TEXT NOT NULL,
                        position TEXT NOT NULL,
                        rank TEXT NOT NULL,
                        name TEXT NOT NULL,
                        present INTEGER NOT NULL,
                        reason TEXT NOT NULL DEFAULT '',
                        note TEXT NOT NULL DEFAULT '',
                        PRIMARY KEY (record_date, position, rank, name)
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_attendance_records_date ON attendance_records(record_date)"
                )
                connection.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось инициализировать базу данных: {str(e)}")

    def load_employees(self):
        """Загрузить сотрудников из employees.txt."""
        try:
            path = self.get_resource_path("employees.txt")
            if not os.path.exists(path):
                messagebox.showerror("Ошибка", f"Файл employees.txt не найден: {path}")
                return []

            data = []
            with open(path, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    parts = [part.strip() for part in line.split(";")]
                    if len(parts) != 3:
                        messagebox.showwarning(
                            "Предупреждение",
                            f"Неверный формат в employees.txt, строка {line_num}: {line}"
                        )
                        continue
                    data.append(parts)

            if not data:
                messagebox.showwarning("Предупреждение", "Файл employees.txt пустой")
            return data
        except OSError as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки employees.txt: {str(e)}")
            return []

    def load_reasons(self):
        """Загрузить причины отсутствия из reasons.txt."""
        try:
            path = self.get_resource_path("reasons.txt")
            if not os.path.exists(path):
                messagebox.showerror("Ошибка", f"Файл reasons.txt не найден: {path}")
                return []

            with open(path, "r", encoding="utf-8") as file:
                reasons = [line.strip() for line in file if line.strip()]

            if not reasons:
                messagebox.showwarning("Предупреждение", "Файл reasons.txt пустой")
            return reasons
        except OSError as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки reasons.txt: {str(e)}")
            return []

    def setup_ui(self):
        """Настроить интерфейс."""
        headers_frame = ctk.CTkFrame(self.app)
        headers_frame.pack(fill="x", padx=10, pady=(10, 0))

        column_widths = [50, 180, 140, 220, 130, 220, 220]
        for col, width in enumerate(column_widths):
            headers_frame.grid_columnconfigure(col, minsize=width)

        headers = [
            "№",
            "Должность",
            "Звание",
            "Ф.И.О",
            "Присутствует",
            "Причина отсутствия",
            "Примечание",
        ]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                headers_frame,
                text=text,
                font=("Arial", 14, "bold"),
                anchor="w",
                justify="left",
            ).grid(row=0, column=col, padx=10, pady=5, sticky="w")

        self.frame = ctk.CTkScrollableFrame(self.app)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)
        for col, width in enumerate(column_widths):
            self.frame.grid_columnconfigure(col, minsize=width)

        self.create_employee_rows()
        self.load_today_data()

        button_frame = ctk.CTkFrame(self.app)
        button_frame.pack(fill="x", padx=10, pady=10)

        self.generate_button = ctk.CTkButton(
            button_frame,
            text="Сгенерировать отчет",
            command=self.generate_report,
        )
        self.generate_button.pack(side="left", padx=10)

        self.preview_button = ctk.CTkButton(
            button_frame,
            text="Предварительный просмотр",
            command=self.preview_report,
        )
        self.preview_button.pack(side="left", padx=10)

        self.show_dates_button = ctk.CTkButton(
            button_frame,
            text="Даты отчетов",
            command=self.show_available_report_dates,
        )
        self.show_dates_button.pack(side="left", padx=10)

        self.clear_history_button = ctk.CTkButton(
            button_frame,
            text="Очистить историю",
            command=self.clear_history,
        )
        self.clear_history_button.pack(side="left", padx=10)

        today_str = datetime.now().strftime("%d.%m.%Y")
        self.from_date_var = ctk.StringVar(value=today_str)
        self.to_date_var = ctk.StringVar(value=today_str)

        ctk.CTkLabel(button_frame, text="Период с:").pack(side="left", padx=5)
        from_frame = ctk.CTkFrame(button_frame)
        from_frame.pack(side="left", padx=5)
        ctk.CTkEntry(from_frame, width=100, textvariable=self.from_date_var).pack(side="left")

        ctk.CTkLabel(button_frame, text="по:").pack(side="left", padx=5)
        to_frame = ctk.CTkFrame(button_frame)
        to_frame.pack(side="left", padx=5)
        ctk.CTkEntry(to_frame, width=100, textvariable=self.to_date_var).pack(side="left")

        self.period_button = ctk.CTkButton(
            button_frame,
            text="Информация за период",
            command=self.show_period_info,
        )
        self.period_button.pack(side="left", padx=10)

        self.exit_button = ctk.CTkButton(button_frame, text="Выход", command=self.app.quit)
        self.exit_button.pack(side="right", padx=10)

    def create_employee_rows(self):
        """Создать строки сотрудников."""
        for i, employee in enumerate(self.employees, start=1):
            position, rank, name = employee
            row_index = i - 1

            ctk.CTkLabel(self.frame, text=str(i), anchor="w").grid(
                row=row_index, column=0, padx=10, pady=5, sticky="w"
            )
            ctk.CTkLabel(self.frame, text=position, anchor="w").grid(
                row=row_index, column=1, padx=10, pady=5, sticky="w"
            )
            ctk.CTkLabel(self.frame, text=rank, anchor="w").grid(
                row=row_index, column=2, padx=10, pady=5, sticky="w"
            )
            ctk.CTkLabel(self.frame, text=name, anchor="w").grid(
                row=row_index, column=3, padx=10, pady=5, sticky="w"
            )

            present_var = ctk.BooleanVar(value=False)
            reason_var = ctk.StringVar()
            note_var = ctk.StringVar()

            checkbox = ctk.CTkCheckBox(self.frame, text="", variable=present_var)
            checkbox.grid(row=row_index, column=4, padx=10, pady=5, sticky="w")
            checkbox.deselect()

            combo = ctk.CTkComboBox(self.frame, values=self.reasons, variable=reason_var)
            combo.grid(row=row_index, column=5, padx=10, pady=5, sticky="w")
            combo.set("")

            note_entry = ctk.CTkEntry(
                self.frame,
                textvariable=note_var,
                placeholder_text="Примечание",
            )
            note_entry.grid(row=row_index, column=6, padx=10, pady=5, sticky="w")
            note_entry.configure(state="disabled")

            def sync_row_state(
                present_var=present_var,
                reason_var=reason_var,
                note_var=note_var,
                combo=combo,
                note_entry=note_entry,
            ):
                if present_var.get():
                    reason_var.set("")
                    note_var.set("")
                    combo.configure(state="disabled")
                    note_entry.configure(state="disabled")
                    return

                combo.configure(state="normal")
                if reason_var.get():
                    note_entry.configure(state="normal")
                else:
                    note_var.set("")
                    note_entry.configure(state="disabled")

            def on_present_change(sync_row_state=sync_row_state):
                sync_row_state()

            def on_reason_change(choice, present_var=present_var, reason_var=reason_var, sync_row_state=sync_row_state):
                reason_var.set(choice)
                if choice:
                    present_var.set(False)
                sync_row_state()

            checkbox.configure(command=on_present_change)
            combo.configure(command=on_reason_change)
            sync_row_state()

            self.rows.append(
                {
                    "position": position,
                    "rank": rank,
                    "name": name,
                    "present": present_var,
                    "reason": reason_var,
                    "note": note_var,
                    "sync_state": sync_row_state,
                }
            )

    def validate_data(self):
        """Проверить заполненность статусов."""
        for row in self.rows:
            present = row["present"].get()
            reason = row["reason"].get().strip()

            if not present and not reason:
                messagebox.showerror(
                    "Ошибка",
                    f"Не заполнен статус сотрудника:\n{row['name']}"
                )
                return False

            if present and reason:
                messagebox.showerror(
                    "Ошибка",
                    f"Конфликт данных у:\n{row['name']}"
                )
                return False

        return True

    def load_today_data(self):
        """Подгрузить записи за сегодня в форму."""
        today_str = datetime.now().strftime("%d.%m.%Y")
        today_records = self.load_records_by_date(today_str)
        if not today_records:
            return

        records_by_employee = {
            (row["position"], row["rank"], row["name"]): row
            for row in today_records
        }

        for row in self.rows:
            record = records_by_employee.get((row["position"], row["rank"], row["name"]))
            if not record:
                continue

            row["present"].set(record["present"] == "1")
            row["reason"].set(record["reason"])
            row["note"].set(record["note"])
            row["sync_state"]()

    def parse_date_string(self, date_str):
        """Преобразовать строку даты в объект date."""
        try:
            return datetime.strptime(date_str, "%d.%m.%Y").date()
        except (TypeError, ValueError):
            return None

    def load_records_by_date(self, date_str):
        """Загрузить записи за конкретную дату."""
        try:
            with self.connect_db() as connection:
                cursor = connection.execute(
                    """
                    SELECT record_date, position, rank, name, present, reason, note
                    FROM attendance_records
                    WHERE record_date = ?
                    ORDER BY position, rank, name
                    """,
                    (date_str,),
                )
                return [
                    {
                        "date": row["record_date"],
                        "position": row["position"],
                        "rank": row["rank"],
                        "name": row["name"],
                        "present": str(row["present"]),
                        "reason": row["reason"],
                        "note": row["note"],
                    }
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            messagebox.showwarning("Предупреждение", f"Не удалось прочитать историю: {str(e)}")
            return []

    def build_short_name(self, full_name):
        """Сократить ФИО до формата 'Фамилия И.'."""
        parts = full_name.split()
        if len(parts) > 1 and parts[1]:
            return f"{parts[0]} {parts[1][0]}."
        return full_name

    def build_absent_person_text(self, name, note):
        """Сформировать запись по сотруднику с примечанием."""
        text = self.build_short_name(name)
        note = note.strip()
        if note:
            text += f" ({note})"
        return text

    def build_grouped_absence_lines(self, absent_entries):
        """Сгруппировать отсутствующих по одинаковой причине."""
        grouped = {}
        reason_order = []

        for entry in absent_entries:
            reason = entry["reason"].strip() or "Без причины"
            person_text = self.build_absent_person_text(entry["name"], entry["note"])
            if reason not in grouped:
                grouped[reason] = []
                reason_order.append(reason)
            grouped[reason].append(person_text)

        return [f"{reason}: {', '.join(grouped[reason])}" for reason in reason_order]

    def collect_report_data(self):
        """Собрать данные для превью и сохранения отчета."""
        date_str = datetime.now().strftime("%d.%m.%Y")
        present_count = 0
        absent_entries = []

        for row in self.rows:
            if row["present"].get():
                present_count += 1
                continue

            absent_entries.append(
                {
                    "reason": row["reason"].get(),
                    "name": row["name"],
                    "note": row["note"].get(),
                }
            )

        absent_list = self.build_grouped_absence_lines(absent_entries)

        return {
            "date_str": date_str,
            "present_count": present_count,
            "absent_count": len(absent_entries),
            "absent_list": absent_list,
        }

    def build_preview_text(self, report_data):
        """Сформировать текст предварительного просмотра."""
        absent_block = "\n".join(report_data["absent_list"]) if report_data["absent_list"] else "Нет отсутствующих"
        return (
            f"ОТЧЕТ\n"
            f"о присутствии сотрудников на {report_data['date_str']}\n\n"
            f"Общее количество сотрудников: {len(self.rows)}\n"
            f"Присутствующих: {report_data['present_count']}\n"
            f"Отсутствующих: {report_data['absent_count']}\n\n"
            f"Список отсутствующих сотрудников:\n\n{absent_block}\n\n"
            f"Начальник отдела\n____________________\n[Ф.И.О.]"
        )

    def generate_report(self):
        """Сгенерировать .docx-отчет."""
        try:
            if not self.validate_data():
                return

            template_path = self.get_resource_path("template.docx")
            if not os.path.exists(template_path):
                messagebox.showerror("Ошибка", f"Файл template.docx не найден: {template_path}")
                return

            from docxtpl import DocxTemplate

            doc = DocxTemplate(template_path)
            report_data = self.collect_report_data()

            context = {
                "DATE": report_data["date_str"],
                "NA_LICO": len(self.rows),
                "PRESENT": report_data["present_count"],
                "ABSENT_TOTAL": report_data["absent_count"],
                "ABSENT_LIST": "\n".join(report_data["absent_list"]),
            }

            doc.render(context)

            filename = self.get_report_path(f"Отчет_{report_data['date_str']}.docx")
            doc.save(filename)
            self.save_history(report_data["date_str"])
            self.open_file(filename)

            messagebox.showinfo("Успех", f"Отчет сохранен: {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при генерации отчета: {str(e)}")

    def save_history(self, date_str):
        """Сохранить текущую ведомость в SQLite."""
        records = [
            (
                date_str,
                row["position"],
                row["rank"],
                row["name"],
                1 if row["present"].get() else 0,
                row["reason"].get().strip(),
                row["note"].get().strip(),
            )
            for row in self.rows
        ]

        try:
            with self.connect_db() as connection:
                connection.execute(
                    "DELETE FROM attendance_records WHERE record_date = ?",
                    (date_str,),
                )
                connection.executemany(
                    """
                    INSERT INTO attendance_records
                    (record_date, position, rank, name, present, reason, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
                connection.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить историю: {str(e)}")

    def clear_history(self):
        """Очистить историю в базе."""
        if not messagebox.askyesno(
            "Подтверждение",
            "Очистить всю историю? Это действие нельзя отменить."
        ):
            return

        try:
            with self.connect_db() as connection:
                connection.execute("DELETE FROM attendance_records")
                connection.commit()
            messagebox.showinfo("Успех", "История успешно очищена.")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить историю: {str(e)}")

    def show_available_report_dates(self):
        """Показать даты, для которых есть записи."""
        try:
            with self.connect_db() as connection:
                cursor = connection.execute(
                    "SELECT DISTINCT record_date FROM attendance_records"
                )
                raw_dates = [row["record_date"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать историю: {str(e)}")
            return

        valid_dates = [date for date in raw_dates if self.parse_date_string(date) is not None]
        if not valid_dates:
            messagebox.showinfo("Информация", "Записи истории отсутствуют.")
            return

        sorted_dates = sorted(valid_dates, key=self.parse_date_string)

        dates_window = ctk.CTkToplevel(self.app)
        dates_window.title("Доступные даты отчетов")
        dates_window.geometry("400x400")
        dates_window.attributes("-topmost", True)
        dates_window.grab_set()
        dates_window.focus_force()

        info_label = ctk.CTkLabel(
            dates_window,
            text="Даты, для которых есть отчеты:",
            font=("Arial", 14, "bold"),
        )
        info_label.pack(padx=10, pady=(10, 5), anchor="w")

        frame = ctk.CTkScrollableFrame(dates_window)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        for date in sorted_dates:
            ctk.CTkLabel(frame, text=date, anchor="w", font=("Arial", 12)).pack(
                fill="x", padx=5, pady=3
            )

        close_button = ctk.CTkButton(dates_window, text="Закрыть", command=dates_window.destroy)
        close_button.pack(pady=10)

    def load_history(self, date_from, date_to):
        """Загрузить записи истории за период."""
        try:
            with self.connect_db() as connection:
                cursor = connection.execute(
                    """
                    SELECT record_date, position, rank, name, present, reason, note
                    FROM attendance_records
                    """
                )
                records = []
                for row in cursor.fetchall():
                    row_date = self.parse_date_string(row["record_date"])
                    if row_date is None or not (date_from <= row_date <= date_to):
                        continue

                    records.append(
                        {
                            "date": row["record_date"],
                            "position": row["position"],
                            "rank": row["rank"],
                            "name": row["name"],
                            "present": str(row["present"]),
                            "reason": row["reason"],
                            "note": row["note"],
                        }
                    )
                return records
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать историю: {str(e)}")
            return []

    def show_period_info(self):
        """Показать информацию за выбранный период."""
        try:
            date_from = datetime.strptime(self.from_date_var.get(), "%d.%m.%Y").date()
            date_to = datetime.strptime(self.to_date_var.get(), "%d.%m.%Y").date()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите даты в формате ДД.ММ.ГГГГ")
            return

        if date_from > date_to:
            messagebox.showerror("Ошибка", "Дата начала должна быть раньше даты конца")
            return

        records = self.load_history(date_from, date_to)
        if not records:
            messagebox.showinfo("Информация", "Записи за выбранный период не найдены")
            return

        dates = sorted({row["date"] for row in records}, key=self.parse_date_string)
        summary = {
            date: {"present": 0, "absent_entries": []}
            for date in dates
        }

        for row in records:
            if row["present"] == "1":
                summary[row["date"]]["present"] += 1
                continue

            summary[row["date"]]["absent_entries"].append(
                {
                    "reason": row["reason"],
                    "name": row["name"],
                    "note": row["note"],
                }
            )

        report_text = (
            f"Информация за период с {date_from.strftime('%d.%m.%Y')} "
            f"по {date_to.strftime('%d.%m.%Y')}\n\n"
        )
        report_text += f"Дней в отчете: {len(dates)}\n\n"

        for date in dates:
            absent_entries = summary[date]["absent_entries"]
            absent_lines = self.build_grouped_absence_lines(absent_entries)
            report_text += (
                f"{date}: присутствующих {summary[date]['present']}, "
                f"отсутствующих {len(absent_entries)}\n"
            )
            if absent_lines:
                report_text += "  Отсутствуют:\n"
                for line in absent_lines:
                    report_text += f"    {line}\n"
                report_text += "\n"

        preview_window = ctk.CTkToplevel(self.app)
        preview_window.title("Данные за период")
        preview_window.geometry("650x450")
        preview_window.attributes("-topmost", True)
        preview_window.grab_set()
        preview_window.focus_force()

        frame = ctk.CTkScrollableFrame(preview_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        label = ctk.CTkLabel(frame, text=report_text, justify="left", font=("Arial", 12))
        label.pack(anchor="w", padx=10, pady=10)

        close_button = ctk.CTkButton(preview_window, text="Закрыть", command=preview_window.destroy)
        close_button.pack(pady=10)

    def preview_report(self):
        """Показать предварительный просмотр отчета."""
        try:
            if not self.validate_data():
                return

            report_data = self.collect_report_data()
            report_text = self.build_preview_text(report_data)

            preview_window = ctk.CTkToplevel(self.app)
            preview_window.title("Предварительный просмотр отчета")
            preview_window.geometry("600x400")
            preview_window.attributes("-topmost", True)
            preview_window.grab_set()
            preview_window.focus_force()

            frame = ctk.CTkScrollableFrame(preview_window)
            frame.pack(fill="both", expand=True, padx=10, pady=10)

            label = ctk.CTkLabel(frame, text=report_text, justify="left", font=("Arial", 12))
            label.pack(anchor="w", padx=10, pady=10)

            close_button = ctk.CTkButton(preview_window, text="Закрыть", command=preview_window.destroy)
            close_button.pack(pady=10)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при предварительном просмотре: {str(e)}")

    def open_file(self, filepath):
        """Открыть файл стандартной программой."""
        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":
                subprocess.run(["open", filepath], check=False)
            else:
                subprocess.run(["xdg-open", filepath], check=False)
        except Exception as e:
            messagebox.showwarning("Предупреждение", f"Не удалось автоматически открыть файл: {str(e)}")

    def run(self):
        """Запустить приложение."""
        self.app.mainloop()


if __name__ == "__main__":
    app = AttendanceApp()
    app.run()
