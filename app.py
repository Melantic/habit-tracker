import os
import json
import uuid
from datetime import date, timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for # type: ignore
from collections import defaultdict

app = Flask(__name__, template_folder="templates")

DB_PATH = os.path.join(os.path.dirname(__file__), "db.json")

habits = []

def load_db():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_db(habits):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(habits, f, indent=2)

@app.route("/", methods=["GET"])
def index():
    habits = load_db()
    auto_close_missed_streaks(habits)

    # Build heatmap data
    end = date.today()
    start = end - timedelta(days=364)
    counts = build_heatmap_counts(habits, start, end)

    # Build days/weeks
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)

    weeks = []
    week = []
    padding = days[6].weekday()  # Align Sunday (6)
    week = [None] * padding
    for day in days:
        week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        week += [None] * (7 - len(week))
        weeks.append(week)

    return render_template(
        "index.html",
        habits=habits,
        now_date=date.today().isoformat(),
        weeks=weeks,
        counts=counts,
        start=start,
        end=end
    )

@app.route("/add", methods=["POST"])
def add():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("index"))

    habits = load_db()
    habits.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "last_done": "",
        "streak": 0,
        "best_streak": 0,
        "completed_dates": []
        })
    save_db(habits)
    return redirect(url_for("index"))

@app.route("/delete/<habit_id>", methods=["POST"])
def delete(habit_id):
    habits = load_db()
    new_habits = [habit for habit in habits if habit["id"] != habit_id]
    if len(new_habits) == len(habits):
        return redirect(url_for("index"))
    else:
        save_db(new_habits)
    return redirect(url_for("index"))
    
@app.route("/edit/<habit_id>", methods=["POST"])
def edit(habit_id):
    new_name = request.form.get("name", "").strip()
    if not new_name:
        return redirect(url_for("index"))
    
    habits = load_db()
    found = False
    for habit in habits:
        if habit["id"] == habit_id:
            habit["name"] = new_name
            found = True
            break

    if found:
        save_db(habits)

    return redirect(url_for("index"))

@app.route("/done/<habit_id>", methods=["POST"])
def mark_done(habit_id):
    habits = load_db()
    today = date.today()
    today_str = today.isoformat()
    yesterday = today - timedelta(days=1)
    for habit in habits:
        if habit["id"] == habit_id:
            add_completed_date_once(habit, today_str)

            if habit["last_done"] == today_str:
                break
            
            try:
                last = date.fromisoformat(habit["last_done"]) if habit["last_done"] else None
            except ValueError:
                last = None

            if last == yesterday:
                habit["streak"] += 1
            else:
                habit["streak"] = 1

            habit["last_done"] = today_str
            habit["best_streak"] = max(habit["best_streak"], habit["streak"])

            save_db(habits)
            break

    return redirect(url_for("index"))

@app.route("/heatmap")
def heatmap():
    habits = load_db()
    auto_close_missed_streaks(habits)

    end = date.today()
    start = end - timedelta(days=364)

    habit_id = request.args.get("habit_id")
    counts = build_heatmap_counts(habits, start, end, habit_id)

    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)

    weeks = []
    week = []
    padding = days[6].weekday()
    week = [None] * padding

    for day in days:
        week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []

    if week:
        week += [None] * (7 - len(week))
        weeks.append(week)

    return render_template("heatmap.html", weeks=weeks, counts=counts, start=start, end=end, habits=habits, selected_habit_id=habit_id)

def build_heatmap_counts(habits, start, end, habit_id=None):
    counts = defaultdict(int)
    for habit in habits:
        if habit_id and habit["id"] != habit_id:
            continue
        for d in set(habit.get("completed_dates", [])):
            try:
                dt = date.fromisoformat(d)
            except ValueError:
                continue
            if start <= dt <= end:
                counts[dt.isoformat()] += 1
    
    return counts

def add_completed_date_once(habit, today_str):
    if today_str not in habit["completed_dates"]:
        habit["completed_dates"].append(today_str)

def auto_close_missed_streaks(habits, today=None):
    today = today or date.today()
    changed = False

    for habit in habits:
        last = None
        if habit.get("last_done"):
            try:
                last = date.fromisoformat(habit["last_done"])
            except ValueError:
                pass

        if last is None or (today - last).days > 1:
            if habit.get("streak", 0) != 0:
                habit["streak"] = 0
                changed = True

    if changed:
        save_db(habits)

if __name__ == '__main__':
    app.run(debug=True)