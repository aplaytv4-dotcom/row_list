import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

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


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class AttendanceApp:
    def __init__(self):
        init_db()

        processed = sync_employees_from_file()
        if processed == 0:
            messagebox.showwarning(
                "Внимание",
                "Сотрудники не загружены. Проверь файл employees.txt"
            )

        self.app = ctk.CTk()
        self.app.title("Учёт присутствия 7.0")

        self.today_db = datetime.now().strftime("%Y-%m-%d")
        self.today_view = datetime.now().strftime("%d.%m.%Y")

        self.reasons = load_reasons()
        self.employees = get_employees()
        self.today_data = load_today_status(self.today_db)

        self.rows = []

        self.build_ui()
        self.auto_resize_window()

    def build_ui(self):
        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self.app)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)

        title = ctk.CTkLabel(
            header_frame,
            text="Учёт присутствия сотрудников",
            font=("Arial", 22, "bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=10)

        date_label = ctk.CTkLabel(
            header_frame,
            text=f"Текущая дата: {self.today_view}",
            font=("Arial", 18, "bold"),
        )
        date_label.grid(row=0, column=1, sticky="e", padx=15, pady=10)

        self.frame = ctk.CTkFrame(self.app)
        self.frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        headers = [
            "№",
            "Подразделение",
            "Должность",
            "Звание",
            "ФИО",
            "Присутствует",
            "Причина",
            "Комментарий",
        ]

        column_widths = [40, 150, 150, 110, 220, 110, 180, 250]

        for col, text in enumerate(headers):
            self.frame.grid_columnconfigure(col, minsize=column_widths[col])
            ctk.CTkLabel(
                self.frame,
                text=text,
                font=("Arial", 14, "bold"),
            ).grid(row=0, column=col, padx=6, pady=6, sticky="w")

        for index, emp in enumerate(self.employees, start=1):
            self.add_employee_row(index, emp)

        buttons = ctk.CTkFrame(self.app)
        buttons.grid(row=2, column=0, pady=(0, 10), padx=10)

        ctk.CTkButton(
            buttons,
            text="Все присутствуют",
            command=self.mark_all_present,
            width=170,
        ).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(
            buttons,
            text="Сохранить",
            command=self.save_all,
            width=170,
        ).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(
            buttons,
            text="Отчёт за месяц",
            command=self.report_month,
            width=170,
        ).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(
            buttons,
            text="Отчёт за квартал",
            command=self.report_quarter,
            width=170,
        ).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(
            buttons,
            text="Отчёт за год",
            command=self.report_year,
            width=170,
        ).pack(side="left", padx=8, pady=8)

    def auto_resize_window(self):
        self.app.update_idletasks()

        req_width = self.app.winfo_reqwidth()
        req_height = self.app.winfo_reqheight()

        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()

        max_width = screen_width - 40
        max_height = screen_height - 80

        final_width = min(req_width, max_width)
        final_height = min(req_height, max_height)

        x = max((screen_width - final_width) // 2, 0)
        y = max((screen_height - final_height) // 2, 0)

        self.app.geometry(f"{final_width}x{final_height}+{x}+{y}")

        if req_width > max_width or req_height > max_height:
            try:
                self.app.state("zoomed")
            except Exception:
                self.app.geometry(f"{max_width}x{max_height}+0+0")

        self.app.minsize(1100, 600)

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
        comment_var = ctk.StringVar(value="")

        if not is_vacant:
            saved = self.today_data.get(emp_id)
            if saved:
                if saved["status"] == "Присутствует":
                    present_var.set(True)
                else:
                    present_var.set(False)
                    reason_var.set(saved["reason"])
                    # комментарий подгружаем только для "Отпросился"
                    if saved["reason"] == "Отпросился":
                        comment_var.set(saved["comment"])
                    else:
                        comment_var.set("")

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
            width=170,
        )
        combo.grid(row=row_number, column=6, padx=6, pady=4)

        entry = ctk.CTkEntry(
            self.frame,
            textvariable=comment_var,
            width=240,
            placeholder_text="Укажите причину, почему отпросился",
        )
        entry.grid(row=row_number, column=7, padx=6, pady=4)

        row_data = {
            "emp_id": emp_id,
            "department": department,
            "position": position,
            "rank": rank,
            "name": name,
            "present": present_var,
            "reason": reason_var,
            "comment": comment_var,
            "label": name_label,
            "combo": combo,
            "entry": entry,
            "checkbox": checkbox,
            "is_vacant": is_vacant,
            "row_number": row_number,
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
            row["combo"].configure(state="disabled")
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
        self.update_comment_visibility(row)

    def update_comment_visibility(self, row):
        reason = row["reason"].get().strip()

        if reason == "Отпросился":
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
        comment = row["comment"].get().strip()

        if reason == "Отпросился":
            row["entry"].grid()
            row["entry"].configure(state="normal")
            if not comment:
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

    def validate(self):
        if not self.rows:
            messagebox.showerror("Ошибка", "Список сотрудников пуст.")
            return False

        real_rows = [row for row in self.rows if not row["is_vacant"]]
        if not real_rows:
            messagebox.showerror("Ошибка", "Нет реальных сотрудников для учёта.")
            return False

        for row in real_rows:
            is_present = row["present"].get()
            reason = row["reason"].get().strip()
            comment = row["comment"].get().strip()

            if not is_present and not reason:
                messagebox.showerror(
                    "Ошибка",
                    f"Не указана причина отсутствия:\n{row['name']}",
                )
                return False

            if not is_present and reason == "Отпросился" and not comment:
                messagebox.showerror(
                    "Ошибка",
                    f"Для сотрудника {row['name']} нужно указать комментарий, если выбрано 'Отпросился'.",
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
                status = "Отсутствует"
                reason = row["reason"].get().strip()
                comment = row["comment"].get().strip() if reason == "Отпросился" else ""

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

    def save_all(self):
        if not self.validate():
            return

        daily_data = self.build_daily_data()

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
            )
            messagebox.showinfo("Готово", "Данные сохранены и ежедневный отчёт сформирован.")
        except FileNotFoundError as e:
            messagebox.showerror("Ошибка шаблона", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def report_month(self):
        today = datetime.now()
        date_from = today.replace(day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

        employees, attendance_rows = get_month_employee_stats(date_from, date_to)

        try:
            generate_period_report(
                title="Месячный отчет",
                date_from=date_from,
                date_to=date_to,
                employees=employees,
                attendance_rows=attendance_rows,
                staff_total_with_vacancies=len(self.employees),
            )
        except FileNotFoundError as e:
            messagebox.showerror("Ошибка шаблона", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def report_quarter(self):
        today = datetime.now()
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        date_from = today.replace(month=quarter_start_month, day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

        employees, attendance_rows = get_month_employee_stats(date_from, date_to)

        try:
            generate_period_report(
                title="Квартальный отчет",
                date_from=date_from,
                date_to=date_to,
                employees=employees,
                attendance_rows=attendance_rows,
                staff_total_with_vacancies=len(self.employees),
            )
        except FileNotFoundError as e:
            messagebox.showerror("Ошибка шаблона", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def report_year(self):
        today = datetime.now()
        date_from = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

        employees, attendance_rows = get_month_employee_stats(date_from, date_to)

        try:
            generate_period_report(
                title="Годовой отчет",
                date_from=date_from,
                date_to=date_to,
                employees=employees,
                attendance_rows=attendance_rows,
                staff_total_with_vacancies=len(self.employees),
            )
        except FileNotFoundError as e:
            messagebox.showerror("Ошибка шаблона", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{e}")

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    AttendanceApp().run()