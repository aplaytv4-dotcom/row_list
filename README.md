# Учёт присутствия 3.0

Desktop-приложение на Python и CustomTkinter для учёта присутствия сотрудников, генерации Word-отчётов и просмотра истории по датам.

## Возможности

- Загрузка сотрудников из `employees.txt`
- Загрузка причин отсутствия из `reasons.txt`
- Пустые чекбоксы при старте, без автовыбора
- Автоподгрузка записей за текущую дату из `attendance_history.csv`
- Возможность выбрать причину отсутствия или отметить сотрудника как присутствующего
- Если установить чекбокс `Присутствует`, выбранная причина и примечание автоматически очищаются
- Добавление примечаний к отсутствующим
- Предварительный просмотр отчёта
- Генерация `.docx`-отчёта по шаблону `template.docx`
- Просмотр доступных дат отчётов
- Просмотр информации за выбранный период
- Очистка истории

## Структура проекта

- `attendance_app.py` — основной код приложения
- `employees.txt` — список сотрудников
- `reasons.txt` — список причин отсутствия
- `template.docx` — шаблон отчёта
- `attendance_history.csv` — история посещаемости
- `attendance_app.spec` — конфигурация PyInstaller
- `compile.bat` — скрипт сборки `.exe`
- `dist/` — готовая сборка
- `build/` — временные файлы PyInstaller

## Зависимости

```bash
pip install customtkinter python-docx docxtpl pyinstaller
```

## Запуск из исходников

```bash
python attendance_app.py
```

## Сборка в exe

```bash
python -m PyInstaller attendance_app.spec
```

Или:

```bash
compile.bat
```

Готовый файл после сборки:

```text
C:\Users\obidovtz\Desktop\AttendanceApp\dist\attendance_app.exe
```

## Где хранятся файлы

При запуске из `.exe`:

- `employees.txt`, `reasons.txt`, `template.docx` и `attendance_history.csv` читаются и сохраняются рядом с `attendance_app.exe`
- отчёты сохраняются в папку `Отчеты` рядом с `attendance_app.exe`

Для текущей сборки это:

```text
C:\Users\obidovtz\Desktop\AttendanceApp\dist\attendance_history.csv
C:\Users\obidovtz\Desktop\AttendanceApp\dist\Отчеты\
```

При запуске из исходников:

- история сохраняется рядом с `attendance_app.py`
- отчёты сохраняются в папку `Отчеты` рядом с `attendance_app.py`

## Как работает история

- При старте приложение ищет записи за текущую дату и автоматически подставляет их в форму
- При повторном сохранении за ту же дату старые записи за этот день в `attendance_history.csv` заменяются новыми
- Кнопка `Даты отчётов` показывает даты из `attendance_history.csv`
- Кнопка `Информация за период` тоже работает по данным из `attendance_history.csv`

## Формат данных

`employees.txt`:

```text
Инженер;Капитан;Азизов А.С.
Менеджер;Лейтенант;Каримов Б.Б.
Оператор;Сержант;Ибрагимов Д.Д.
```

`reasons.txt`:

```text
otpusk
bolnichniy
otprosilsya
```

## Требования

- Python 3.7+
- customtkinter
- python-docx
- docxtpl
- pyinstaller
