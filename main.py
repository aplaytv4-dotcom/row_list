import os
import sys
import json
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tkcalendar import DateEntry

from database import (
    get_employees,
    get_month_employee_stats,
    init_db,
    load_reasons,
    load_today_status,
    save_status,
    sync_employees_from_file,
)

from reports import (
    generate_daily_report,
    generate_period_report,
)


def get_base_path() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()
WINDOW_CONFIG_FILE = os.path.join(BASE_PATH, "window_config.json")

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class AttendanceApp:
    def __init__(self):
        init_db()

        processed = sync_employees_from_file()
        if processed == 0:
            messagebox.showwarning(
                "Внимание",
                "Список сотрудников не загружен.\nПроверьте файл employees.txt.",
            )

        self.app = ctk.CTk()
        self.app.title("Система учёта присутствия сотрудников")
        self.app.minsize(1400, 800)

        self.today_db = datetime.now().strftime("%Y-%m-%d")
        self.today_view = datetime.now().strftime("%d.%m.%Y")

        self.reasons = load_reasons()
        self.employees = get_employees()
        self.today_data = load_today_status(self.today_db)

        self.chief_name_var = ctk.StringVar(value="")
        self.selected_report_month = ctk.StringVar()
        self.rows = []

        self.build_ui()

        loaded = self.load_window_geometry()
        if not loaded:
            self.center_window()
            try:
                self.app.state("zoomed")
            except Exception:
                pass

        self.app.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================
    # Window geometry
    # =========================

    def load_window_geometry(self):
        try:
            if os.path.exists(WINDOW_CONFIG_FILE):
                with open(WINDOW_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                geometry = data.get("geometry", "").strip()
                is_zoomed = data.get("zoomed", False)

                if geometry:
                    self.app.geometry(geometry)

                self.app.update_idletasks()

                if is_zoomed:
                    try:
                        self.app.state("zoomed")
                    except Exception:
                        pass

                return True
        except Exception:
            pass

        return False

    def save_window_geometry(self):
        try:
            self.app.update_idletasks()

            state = self.app.state()
            data = {
                "geometry": self.app.geometry(),
                "zoomed": state == "zoomed",
            }

            with open(WINDOW_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_close(self):
        self.save_window_geometry()
        self.app.destroy()

    # =========================
    # UI
    # =========================

    def build_ui(self):
        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(self.app)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)

        title = ctk.CTkLabel(
            header_frame,
            text="Система учёта присутствия сотрудников",
            font=("Arial", 22, "bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 4))

        date_label = ctk.CTkLabel(
            header_frame,
            text=f"Сегодня: {self.today_view}",
            font=("Arial", 18, "bold"),
        )
        date_label.grid(row=0, column=1, sticky="e", padx=15, pady=(10, 4))

        chief_label = ctk.CTkLabel(
            header_frame,
            text="Руководитель (Ф.И.О.):",
            font=("Arial", 14, "bold"),
        )
        chief_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))

        chief_entry = ctk.CTkEntry(
            header_frame,
            textvariable=self.chief_name_var,
            width=360,
            placeholder_text="Необязательно",
        )
        chief_entry.grid(row=1, column=1, sticky="e", padx=15, pady=(0, 10))

        self.frame = ctk.CTkScrollableFrame(self.app)
        self.frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        headers = [
            "№",
            "Подразделение",
            "Должность",
            "Звание",
            "Ф.И.О. сотрудника",
            "Присутствует",
            "Причина отсутствия",
            "Примечание",
        ]
        column_widths = [50, 180, 180, 130, 420, 130, 250, 340]

        for col, width in enumerate(column_widths):
            self.frame.grid_columnconfigure(col, minsize=width)

        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.frame,
                text=text,
                font=("Arial", 14, "bold"),
            ).grid(row=0, column=col, padx=6, pady=6, sticky="w")

        for index, emp in enumerate(self.employees, start=1):
            self.add_employee_row(index, emp)

        controls = ctk.CTkFrame(self.app)
        controls.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        controls.grid_columnconfigure(0, weight=1)

        row1 = ctk.CTkFrame(controls)
        row1.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            row1,
            text="Отметить всех",
            command=self.mark_all_present,
            width=180,
        ).pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            row1,
            text="Сохранить сведения",
            command=self.save_all,
            width=180,
        ).pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            row1,
            text="Месячный отчёт",
            command=self.report_month,
            width=180,
        ).pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            row1,
            text="Квартальный отчёт",
            command=self.report_quarter,
            width=180,
        ).pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            row1,
            text="Годовой отчёт",
            command=self.report_year,
            width=180,
        ).pack(side="left", padx=6, pady=6)

        row2 = ctk.CTkFrame(controls)
        row2.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkLabel(
            row2,
            text="Дата отчёта:",
            font=("Arial", 14, "bold"),
        ).pack(side="left", padx=(6, 4), pady=6)

        self.report_date_picker = DateEntry(
            row2,
            width=12,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            date_pattern="dd.mm.yyyy",
            locale="ru_RU",
        )
        self.report_date_picker.pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            row2,
            text="Сформировать отчёт за выбранный день",
            command=self.generate_report_for_selected_date,
            width=280,
        ).pack(side="left", padx=6, pady=6)

        months = self.get_available_report_months()
        self.selected_report_month.set(months[0])

        ctk.CTkLabel(
            row2,
            text="Месяц:",
            font=("Arial", 14, "bold"),
        ).pack(side="left", padx=(20, 4), pady=6)

        self.report_months_combo = ctk.CTkComboBox(
            row2,
            values=months,
            variable=self.selected_report_month,
            state="readonly",
            width=140,
        )
        self.report_months_combo.pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            row2,
            text="Открыть отчёты за месяц",
            command=self.open_selected_report_month,
            width=220,
        ).pack(side="left", padx=6, pady=6)

    def center_window(self):
        self.app.update_idletasks()
        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()

        width = screen_width - 20
        height = screen_height - 80
        x = 0
        y = 0

        self.app.geometry(f"{width}x{height}+{x}+{y}")

    # =========================
    # Reports folders
    # =========================

    def get_reports_root_dir(self):
        return os.path.join(BASE_PATH, "отчеты")

    def get_available_report_months(self):
        reports_root = self.get_reports_root_dir()
        os.makedirs(reports_root, exist_ok=True)

        months = []
        for name in os.listdir(reports_root):
            full_path = os.path.join(reports_root, name)
            if os.path.isdir(full_path):
                months.append(name)

        months.sort(reverse=True)

        if not months:
            months = [datetime.now().strftime("%Y-%m")]

        return months

    def refresh_report_months(self):
        months = self.get_available_report_months()
        self.report_months_combo.configure(values=months)

        current = self.selected_report_month.get().strip()
        if current not in months:
            self.selected_report_month.set(months[0])

    def open_selected_report_month(self):
        month = self.selected_report_month.get().strip()
        if not month:
            messagebox.showerror("Ошибка", "Выберите месяц.")
            return

        folder = os.path.join(self.get_reports_root_dir(), month)

        if not os.path.exists(folder):
            messagebox.showerror("Ошибка", f"Папка отчётов за месяц не найдена:\n{folder}")
            return

        try:
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{e}")

    # =========================
    # Rows
    # =========================

    def add_employee_row(self, row_number, emp):
        emp_id, department, position, rank, name = emp
        is_vacant = name.strip().upper().startswith("ВАКАНТ")

        ctk.CTkLabel(self.frame, text=str(row_number)).grid(
            row=row_number, column=0, padx=6, pady=4, sticky="w"
        )
        ctk.CTkLabel(self.frame, text=department).grid(
            row=row_number, column=1, padx=6, pady=4, sticky="w"
        )
        ctk.CTkLabel(self.frame, text=position).grid(
            row=row_number, column=2, padx=6, pady=4, sticky="w"
        )
        ctk.CTkLabel(self.frame, text=rank).grid(
            row=row_number, column=3, padx=6, pady=4, sticky="w"
        )

        name_label = ctk.CTkLabel(self.frame, text=name)
        name_label.grid(row=row_number, column=4, padx=6, pady=4, sticky="w")

        present_var = ctk.BooleanVar(value=True)
        reason_var = ctk.StringVar(value="")
        note_var = ctk.StringVar(value="")

        if not is_vacant:
            saved = self.today_data.get(emp_id)
            if saved:
                if saved["status"] == "Присутствует":
                    present_var.set(True)
                else:
                    present_var.set(False)
                    reason_var.set(saved["reason"])
                    if saved["reason"] == "Уважительная причина":
                        note_var.set(saved["comment"])
                    else:
                        note_var.set("")

        checkbox = ctk.CTkCheckBox(
            self.frame,
            text="",
            variable=present_var,
            width=30,
        )
        checkbox.grid(row=row_number, column=5, padx=6, pady=4)

        combo = ctk.CTkComboBox(
            self.frame,
            values=self.reasons,
            variable=reason_var,
            state="readonly",
            width=240,
        )
        combo.grid(row=row_number, column=6, padx=(6, 10), pady=4, sticky="w")

        entry = ctk.CTkEntry(
            self.frame,
            textvariable=note_var,
            width=320,
            placeholder_text="Укажите примечание",
        )
        entry.grid(row=row_number, column=7, padx=(10, 6), pady=4, sticky="w")

        row_data = {
            "emp_id": emp_id,
            "department": department,
            "position": position,
            "rank": rank,
            "name": name,
            "present": present_var,
            "reason": reason_var,
            "comment": note_var,
            "label": name_label,
            "combo": combo,
            "entry": entry,
            "checkbox": checkbox,
            "is_vacant": is_vacant,
        }

        checkbox.configure(command=lambda r=row_data: self.toggle_row_state(r))
        combo.configure(command=lambda _choice, r=row_data: self.on_reason_changed(r))
        entry.bind("<KeyRelease>", lambda _event, r=row_data: self.check_comment_required(r))

        self.rows.append(row_data)

        if is_vacant:
            present_var.set(False)
            checkbox.configure(state="disabled")
            combo.configure(state="disabled")
            entry.grid_remove()
            name_label.configure(text_color="gray")
        else:
            self.toggle_row_state(row_data)

    def toggle_row_state(self, row):
        if row["is_vacant"]:
            return

        is_present = row["present"].get()

        if is_present:
            row["reason"].set("")
            row["comment"].set("")
            row["combo"].configure(state="readonly")
            row["entry"].grid_remove()
            row["entry"].configure(state="disabled", border_color="gray")
            row["label"].configure(text_color="black")
        else:
            row["combo"].configure(state="readonly")
            row["label"].configure(text_color="red")
            self.update_comment_visibility(row)

    def on_reason_changed(self, row):
        if row["is_vacant"]:
            return

        reason = row["reason"].get().strip()

        if reason:
            row["present"].set(False)
        else:
            row["present"].set(True)

        self.toggle_row_state(row)

    def update_comment_visibility(self, row):
        if row["is_vacant"]:
            return

        reason = row["reason"].get().strip()

        if reason == "Уважительная причина":
            row["entry"].grid()
            row["entry"].configure(state="normal")
            self.check_comment_required(row)
        else:
            row["comment"].set("")
            row["entry"].configure(state="disabled", border_color="gray")
            row["entry"].grid_remove()

    def check_comment_required(self, row):
        if row["is_vacant"]:
            return

        reason = row["reason"].get().strip()
        note = row["comment"].get().strip()

        if reason == "Уважительная причина":
            row["entry"].grid()
            row["entry"].configure(state="normal")
            if not note:
                row["entry"].configure(border_color="red")
            else:
                row["entry"].configure(border_color="gray")
        else:
            row["comment"].set("")
            row["entry"].configure(state="disabled", border_color="gray")
            row["entry"].grid_remove()

    def mark_all_present(self):
        for row in self.rows:
            if row["is_vacant"]:
                continue
            row["present"].set(True)
            self.toggle_row_state(row)

    # =========================
    # Validation / build data
    # =========================

    def get_chief_name(self):
        return self.chief_name_var.get().strip()

    def validate(self):
        real_rows = [row for row in self.rows if not row["is_vacant"]]
        if not real_rows:
            messagebox.showerror("Ошибка", "Нет реальных сотрудников для учёта.")
            return False

        for row in real_rows:
            is_present = row["present"].get()
            reason = row["reason"].get().strip()
            note = row["comment"].get().strip()

            if not is_present and not reason:
                messagebox.showerror(
                    "Ошибка",
                    f"Не указана причина отсутствия сотрудника:\n{row['name']}",
                )
                return False

            if not is_present and reason == "Уважительная причина" and not note:
                messagebox.showerror(
                    "Ошибка",
                    "Для причины «Уважительная причина» необходимо заполнить поле "
                    f"«Примечание».\nСотрудник: {row['name']}",
                )
                row["entry"].grid()
                row["entry"].configure(state="normal", border_color="red")
                return False

        return True

    def build_daily_data(self):
        data = []

        for row in self.rows:
            if row["is_vacant"]:
                continue

            if row["present"].get():
                status = "Присутствует"
                reason = ""
                comment = ""
            else:
                status = "Отсутствуют по уважительной причине"
                reason = row["reason"].get().strip()
                comment = row["comment"].get().strip() if reason == "Уважительная причина" else ""

            data.append(
                {
                    "emp_id": row["emp_id"],
                    "department": row["department"],
                    "position": row["position"],
                    "rank": row["rank"],
                    "name": row["name"],
                    "status": status,
                    "reason": reason,
                    "comment": comment,
                }
            )

        return data

    # =========================
    # Actions
    # =========================

    def save_all(self):
        if not self.validate():
            return

        daily_data = self.build_daily_data()
        chief_name = self.get_chief_name()

        for row in daily_data:
            save_status(
                row["emp_id"],
                self.today_db,
                row["status"],
                row["reason"],
                row["comment"],
            )

        try:
            generate_daily_report(
                daily_data,
                staff_total_with_vacancies=len(self.employees),
                chief_name=chief_name,
                report_date_db=self.today_db,
            )
            self.refresh_report_months()
            messagebox.showinfo(
                "Операция выполнена",
                "Сведения сохранены.\nЕжедневный отчёт успешно сформирован.",
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def generate_report_for_selected_date(self):
        chief_name = self.get_chief_name()

        try:
            selected_dt = self.report_date_picker.get_date()
            selected_db = selected_dt.strftime("%Y-%m-%d")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить выбранную дату:\n{e}")
            return

        date_data = load_today_status(selected_db)

        daily_data = []
        for row in self.rows:
            if row["is_vacant"]:
                continue

            saved = date_data.get(row["emp_id"])
            if saved:
                status = saved["status"]
                reason = saved["reason"]
                comment = saved["comment"]
            else:
                status = "Присутствует"
                reason = ""
                comment = ""

            daily_data.append(
                {
                    "emp_id": row["emp_id"],
                    "department": row["department"],
                    "position": row["position"],
                    "rank": row["rank"],
                    "name": row["name"],
                    "status": status,
                    "reason": reason,
                    "comment": comment,
                }
            )

        try:
            generate_daily_report(
                daily_data,
                staff_total_with_vacancies=len(self.employees),
                chief_name=chief_name,
                report_date_db=selected_db,
            )
            self.refresh_report_months()
            messagebox.showinfo(
                "Готово",
                "Ежедневный отчёт за выбранную дату сформирован.",
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def report_month(self):
        if not self.validate():
            return

        today = datetime.now()
        date_from = today.replace(day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")
        chief_name = self.get_chief_name()

        employees, attendance_rows = get_month_employee_stats(date_from, date_to)

        try:
            generate_period_report(
                title="Месячный отчёт",
                date_from=date_from,
                date_to=date_to,
                employees=employees,
                attendance_rows=attendance_rows,
                staff_total_with_vacancies=len(self.employees),
                chief_name=chief_name,
            )
            self.refresh_report_months()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def report_quarter(self):
        if not self.validate():
            return

        today = datetime.now()
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        date_from = today.replace(month=quarter_start_month, day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")
        chief_name = self.get_chief_name()

        employees, attendance_rows = get_month_employee_stats(date_from, date_to)

        try:
            generate_period_report(
                title="Квартальный отчёт",
                date_from=date_from,
                date_to=date_to,
                employees=employees,
                attendance_rows=attendance_rows,
                staff_total_with_vacancies=len(self.employees),
                chief_name=chief_name,
            )
            self.refresh_report_months()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def report_year(self):
        if not self.validate():
            return

        today = datetime.now()
        date_from = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")
        chief_name = self.get_chief_name()

        employees, attendance_rows = get_month_employee_stats(date_from, date_to)

        try:
            generate_period_report(
                title="Годовой отчёт",
                date_from=date_from,
                date_to=date_to,
                employees=employees,
                attendance_rows=attendance_rows,
                staff_total_with_vacancies=len(self.employees),
                chief_name=chief_name,
            )
            self.refresh_report_months()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    app = AttendanceApp()
    app.run()