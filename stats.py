from collections import Counter

import matplotlib.pyplot as plt


def stats_reason(attendance_rows) -> None:
    counter = Counter()

    for _, _, status, reason, _ in attendance_rows:
        if status == "Отсутствует" and reason:
            counter[reason] += 1

    if not counter:
        return

    labels = list(counter.keys())
    values = list(counter.values())

    plt.figure(figsize=(8, 6))
    plt.pie(values, labels=labels, autopct="%1.1f%%")
    plt.title("Причины отсутствия")
    plt.show()