import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import csv
import os
import sys
import subprocess
import platform

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class AttendanceApp:
    """Класс для приложения учёта присутствия сотрудников."""

    def __init__(self):
        """Инициализация приложения."""
        self.app = ctk.CTk()
        self.app.title("Учёт присутствия 3.0")
        self.app.geometry("1200x650")

        self.base_path = self.get_base_path()
        self.reports_path = self.get_reports_path()
        self.history_path = self.get_resource_path("attendance_history.csv")
        self.employees = self.load_employees()
        self.reasons = self.load_reasons()
        self.rows = []
        self.date_popup = None

        self.setup_ui()

    def get_resource_path(self, filename):
        """Получить путь к файлу-ресурсу рядом с приложением."""
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), filename)
        return os.path.join(self.base_path, filename)

    def get_report_path(self, filename):
        """Получить путь к файлу отчёта в папке рядом с приложением."""
        return os.path.join(self.reports_path, filename)

    def get_base_path(self):
        """Получить базовый путь к файлам приложения."""
        if getattr(sys, 'frozen', False):
            return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        return os.path.dirname(__file__)

    def get_reports_path(self):
        """Папка для отчётов рядом с exe-файлом или исходником."""
        reports_dir = os.path.join(os.path.dirname(self.get_resource_path("attendance_app.py")), "Отчеты")
        os.makedirs(reports_dir, exist_ok=True)
        return reports_dir

    def load_employees(self):
        """Загрузить список сотрудников из файла employees.txt."""
        try:
            path = self.get_resource_path("employees.txt")
            if not os.path.exists(path):
                messagebox.showerror("Ошибка", f"Файл employees.txt не найден: {path}")
                return []
            with open(path, "r", encoding="utf-8") as f:
                data = []
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(";")
                    if len(parts) != 3:
                        messagebox.showwarning("Предупреждение", f"Неверный формат в employees.txt, строка {line_num}: {line}")
                        continue
                    data.append(parts)
                if not data:
                    messagebox.showwarning("Предупреждение", "Файл employees.txt пустой")
                return data
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки employees.txt: {str(e)}")
            return []

    def load_reasons(self):
        """Загрузить список причин отсутствия из файла reasons.txt."""
        try:
            path = self.get_resource_path("reasons.txt")
            if not os.path.exists(path):
                messagebox.showerror("Ошибка", f"Файл reasons.txt не найден: {path}")
                return []
            with open(path, "r", encoding="utf-8") as f:
                reasons = [line.strip() for line in f if line.strip()]
                if not reasons:
                    messagebox.showwarning("Предупреждение", "Файл reasons.txt пустой")
                return reasons
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки reasons.txt: {str(e)}")
            return []

    def setup_ui(self):
        """Настроить пользовательский интерфейс."""
        # Фиксированные заголовки
        headers_frame = ctk.CTkFrame(self.app)
        headers_frame.pack(fill="x", padx=10, pady=(10, 0))

        headers = ["№", "Должность", "Звание", "Ф.И.О", "Присутствует", "Причина отсутствия", "Примечание"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(headers_frame, text=text, font=("Arial", 14, "bold")).grid(row=0, column=col, padx=10, pady=5)

        self.frame = ctk.CTkScrollableFrame(self.app)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_employee_rows()
        self.load_today_data()

        # Кнопки
        button_frame = ctk.CTkFrame(self.app)
        button_frame.pack(fill="x", padx=10, pady=10)

        self.generate_button = ctk.CTkButton(button_frame, text="Сгенерировать отчёт", command=self.generate_report)
        self.generate_button.pack(side="left", padx=10)

        self.preview_button = ctk.CTkButton(button_frame, text="Предварительный просмотр", command=self.preview_report)
        self.preview_button.pack(side="left", padx=10)

        self.show_dates_button = ctk.CTkButton(button_frame, text="Даты отчётов", command=self.show_available_report_dates)
        self.show_dates_button.pack(side="left", padx=10)

        self.clear_history_button = ctk.CTkButton(button_frame, text="Очистить историю", command=self.clear_history)
        self.clear_history_button.pack(side="left", padx=10)

        self.from_date_var = ctk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))
        self.to_date_var = ctk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))

        ctk.CTkLabel(button_frame, text="Период с:").pack(side="left", padx=5)
        from_frame = ctk.CTkFrame(button_frame)
        from_frame.pack(side="left", padx=5)
        ctk.CTkEntry(from_frame, width=100, textvariable=self.from_date_var).pack(side="left")

        ctk.CTkLabel(button_frame, text="по:").pack(side="left", padx=5)
        to_frame = ctk.CTkFrame(button_frame)
        to_frame.pack(side="left", padx=5)
        ctk.CTkEntry(to_frame, width=100, textvariable=self.to_date_var).pack(side="left")

        self.period_button = ctk.CTkButton(button_frame, text="Информация за период", command=self.show_period_info)
        self.period_button.pack(side="left", padx=10)

        self.exit_button = ctk.CTkButton(button_frame, text="Выход", command=self.app.quit)
        self.exit_button.pack(side="right", padx=10)

    def create_employee_rows(self):
        """Создать строки для каждого сотрудника в интерфейсе."""
        for i, emp in enumerate(self.employees, start=1):
            position, rank, name = emp
            row_index = i - 1

            ctk.CTkLabel(self.frame, text=str(i), anchor="w").grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(self.frame, text=position, anchor="w").grid(row=row_index, column=1, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(self.frame, text=rank, anchor="w").grid(row=row_index, column=2, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(self.frame, text=name, anchor="w").grid(row=row_index, column=3, padx=10, pady=5, sticky="w")

            present_var = ctk.BooleanVar(value=False)
            reason_var = ctk.StringVar()

            checkbox = ctk.CTkCheckBox(self.frame, text="", variable=present_var)
            checkbox.grid(row=row_index, column=4, padx=10, pady=5, sticky="w")
            checkbox.deselect()

            combo = ctk.CTkComboBox(self.frame, values=self.reasons, variable=reason_var)
            combo.grid(row=row_index, column=5, padx=10, pady=5, sticky="w")
            combo.set("")

            note_var = ctk.StringVar()
            note_entry = ctk.CTkEntry(self.frame, textvariable=note_var, placeholder_text="Примечание")
            note_entry.grid(row=row_index, column=6, padx=10, pady=5, sticky="w")
            note_entry.configure(state="disabled")  # Изначально отключено

            def sync_row_state(
                present_var=present_var,
                reason_var=reason_var,
                note_var=note_var,
                checkbox=checkbox,
                combo=combo,
                note_entry=note_entry
            ):
                if present_var.get():
                    reason_var.set("")
                    note_var.set("")
                    checkbox.configure(state="normal")
                    combo.configure(state="disabled")
                    note_entry.configure(state="disabled")
                    return

                combo.configure(state="normal")
                if reason_var.get():
                    checkbox.configure(state="normal")
                    note_entry.configure(state="normal")
                else:
                    checkbox.configure(state="normal")
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

            self.rows.append({
                "position": position,
                "rank": rank,
                "name": name,
                "present": present_var,
                "reason": reason_var,
                "note": note_var,
                "sync_state": sync_row_state
            })

    def validate_data(self):
        """Проверить корректность введённых данных."""
        for r in self.rows:
            present = r["present"].get()
            reason = r["reason"].get()

            if not present and not reason:
                messagebox.showerror("Ошибка", f"Не заполнен статус сотрудника:\n{r['name']}")
                return False

            if present and reason:
                messagebox.showerror("Ошибка", f"Конфликт данных у:\n{r['name']}")
                return False

        return True

    def load_today_data(self):
        """Автоматически подгрузить записи за текущую дату в форму."""
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

            row["present"].set(record.get("present") == "1")
            row["reason"].set(record.get("reason", ""))
            row["note"].set(record.get("note", ""))
            row["sync_state"]()

    def load_records_by_date(self, date_str):
        """Загрузить записи истории за конкретную дату."""
        if not os.path.exists(self.history_path):
            return []

        records = []
        with open(self.history_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("date") == date_str:
                    records.append(row)
        return records

    def build_short_name(self, full_name):
        """Сократить ФИО до формата 'Фамилия И.'."""
        parts = full_name.split()
        if len(parts) > 1 and parts[1]:
            return f"{parts[0]} {parts[1][0]}."
        return full_name

    def collect_report_data(self):
        """Собрать сводные данные для превью и сохранения отчёта."""
        date_str = datetime.now().strftime("%d.%m.%Y")
        present_count = 0
        absent_count = 0
        absent_list = []

        for row in self.rows:
            if row["present"].get():
                present_count += 1
                continue

            absent_count += 1
            line = f"{self.build_short_name(row['name'])} - {row['reason'].get()}"
            note = row["note"].get().strip()
            if note:
                line += f" ({note})"
            absent_list.append(line)

        return {
            "date_str": date_str,
            "present_count": present_count,
            "absent_count": absent_count,
            "absent_list": absent_list,
        }

    def build_preview_text(self, report_data):
        """Сформировать текст предварительного просмотра отчёта."""
        absent_block = "\n".join(report_data["absent_list"]) if report_data["absent_list"] else "Нет отсутствующих"
        return (
            f"ОТЧЁТ\n"
            f"о присутствии сотрудников на {report_data['date_str']}\n\n"
            f"Общее количество сотрудников: {len(self.rows)}\n"
            f"Присутствующих: {report_data['present_count']}\n"
            f"Отсутствующих: {report_data['absent_count']}\n\n"
            f"Список отсутствующих сотрудников:\n\n{absent_block}\n\n"
            f"Начальник отдела\n____________________\n[Ф.И.О.]"
        )

    def generate_report(self):
        """Сгенерировать отчёт на основе введённых данных."""
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
                "ABSENT_LIST": "\n".join(report_data["absent_list"])
            }

            doc.render(context)

            filename = self.get_report_path(f"Отчет_{report_data['date_str']}.docx")
            doc.save(filename)
            self.save_history(report_data["date_str"])

            # Кросс-платформенное открытие файла
            self.open_file(filename)

            messagebox.showinfo("Успех", f"Отчёт сохранён: {filename}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при генерации отчёта: {str(e)}")

    def save_history(self, date_str):
        """Сохранить текущую ведомость в историю."""
        fieldnames = ["date", "position", "rank", "name", "present", "reason", "note"]
        rows = []

        if os.path.exists(self.history_path):
            with open(self.history_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('date') != date_str:
                        rows.append(row)

        for r in self.rows:
            rows.append({
                "date": date_str,
                "position": r["position"],
                "rank": r["rank"],
                "name": r["name"],
                "present": "1" if r["present"].get() else "0",
                "reason": r["reason"].get(),
                "note": r["note"].get()
            })

        with open(self.history_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def clear_history(self):
        """Очистить содержимое файла истории."""
        if not os.path.exists(self.history_path):
            messagebox.showinfo("Информация", "Файл истории отсутствует, нечего очищать.")
            return

        if not messagebox.askyesno("Подтверждение", "Очистить весь файл истории? Это действие нельзя отменить."):
            return

        fieldnames = ["date", "position", "rank", "name", "present", "reason", "note"]
        try:
            with open(self.history_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
            messagebox.showinfo("Успех", "История успешно очищена.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить историю: {str(e)}")


    def show_available_report_dates(self):
        """Показать даты, для которых есть записи отчётов."""
        if not os.path.exists(self.history_path):
            messagebox.showinfo("Информация", "Файл истории не найден. Отчётов нет.")
            return

        dates = set()
        try:
            with open(self.history_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_value = row.get('date')
                    if date_value:
                        dates.add(date_value)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл истории: {str(e)}")
            return

        if not dates:
            messagebox.showinfo("Информация", "Записи истории отсутствуют.")
            return

        sorted_dates = sorted(dates, key=lambda d: datetime.strptime(d, '%d.%m.%Y').date())

        dates_window = ctk.CTkToplevel(self.app)
        dates_window.title("Доступные даты отчётов")
        dates_window.geometry("400x400")
        dates_window.attributes("-topmost", True)
        dates_window.grab_set()
        dates_window.focus_force()

        info_label = ctk.CTkLabel(dates_window, text="Даты, для которых есть отчёты:", font=("Arial", 14, "bold"))
        info_label.pack(padx=10, pady=(10, 5), anchor="w")

        frame = ctk.CTkScrollableFrame(dates_window)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        for date in sorted_dates:
            ctk.CTkLabel(frame, text=date, anchor="w", font=("Arial", 12)).pack(fill="x", padx=5, pady=3)

        close_button = ctk.CTkButton(dates_window, text="Закрыть", command=dates_window.destroy)
        close_button.pack(pady=10)

    def load_history(self, date_from, date_to):
        """Загрузить записи истории за указанный период."""
        if not os.path.exists(self.history_path):
            return []

        records = []
        with open(self.history_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_date = datetime.strptime(row['date'], '%d.%m.%Y').date()
                except Exception:
                    continue
                if date_from <= row_date <= date_to:
                    records.append(row)
        return records

    def show_period_info(self):
        """Показать информацию за выбранный период."""
        try:
            date_from = datetime.strptime(self.from_date_var.get(), '%d.%m.%Y').date()
            date_to = datetime.strptime(self.to_date_var.get(), '%d.%m.%Y').date()
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

        dates = sorted({row['date'] for row in records}, key=lambda d: datetime.strptime(d, '%d.%m.%Y').date())
        summary = {}
        for date in dates:
            summary[date] = {'present': 0, 'absent': 0, 'absent_list': []}

        for row in records:
            name_short = self.build_short_name(row['name'])
            if row['present'] == '1':
                summary[row['date']]['present'] += 1
            else:
                summary[row['date']]['absent'] += 1
                note = row['note']
                line = f"{name_short} - {row['reason']}"
                if note:
                    line += f" ({note})"
                summary[row['date']]['absent_list'].append(line)

        report_text = f"Информация за период с {date_from.strftime('%d.%m.%Y')} по {date_to.strftime('%d.%m.%Y')}\n\n"
        report_text += f"Дней в отчёте: {len(dates)}\n\n"
        for date in dates:
            report_text += f"{date}: присутствующих {summary[date]['present']}, отсутствующих {summary[date]['absent']}\n"
            if summary[date]['absent_list']:
                report_text += "  Отсутствуют:\n"
                for line in summary[date]['absent_list']:
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
        """Показать предварительный просмотр отчёта в новом окне."""
        try:
            if not self.validate_data():
                return

            report_data = self.collect_report_data()
            report_text = self.build_preview_text(report_data)

            # Создать окно предварительного просмотра
            preview_window = ctk.CTkToplevel(self.app)
            preview_window.title("Предварительный просмотр отчёта")
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
        """Кросс-платформенное открытие файла"""
        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", filepath])
            else:  # Linux
                subprocess.run(["xdg-open", filepath])
        except Exception as e:
            messagebox.showwarning("Предупреждение", f"Не удалось автоматически открыть файл: {str(e)}")

    def run(self):
        """Запустить приложение."""
        self.app.mainloop()


if __name__ == "__main__":
    app = AttendanceApp()
    app.run()
