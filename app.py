import os
import json
import uuid
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for # type: ignore

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
    return render_template("index.html", habits=habits, now_date=date.today().isoformat())

@app.route("/add", methods=["POST"])
def add():
    name = request.form.get("name", "").strip()
    if not name:
        #flash("Habit name cannot be empty.")
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
    #flash(f'Habit "{name}" added!')
    return redirect(url_for("index"))

@app.route("/delete/<habit_id>", methods=["POST"])
def delete(habit_id):
    habits = load_db()
    new_habits = [habit for habit in habits if habit["id"] != habit_id]
    if len(new_habits) == len(habits):
        #flash("Habit not found.")
        return redirect(url_for("index"))
    else:
        save_db(new_habits)
        #flash("Habit deleted.")
    return redirect(url_for("index"))
    
@app.route("/edit/<habit_id>", methods=["POST"])
def edit(habit_id):
    new_name = request.form.get("name", "").strip()
    if not new_name:
        #flash("New name cannot be empty.")
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
        #flash("Habit renamed.")
    else:
        #flash("Habit not found.")
        return redirect(url_for("index"))
    return redirect(url_for("index"))

@app.route("/done/<habit_id>", methods=["POST"])
def mark_done(habit_id):
    habits = load_db()
    today = date.today()
    today_str = today.isoformat()
    yesterday = today - timedelta(days=1)
    found = False
    for habit in habits:
        if habit["id"] == habit_id:
            found = True

            habit["completed_dates"].append(today_str)

            if habit["last_done"] == today_str:
                #flash("Already marked done today.")
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
            #flash("Habit marked as done for today!")
            break

    if not found:
        #flash("Habit not found.")
        return redirect(url_for("index"))
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)