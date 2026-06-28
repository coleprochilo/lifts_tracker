from flask import Flask, render_template, request, redirect, url_for
from db import get_conn

app = Flask(__name__)


def _fmt_weight(w):
    return int(w) if w == int(w) else w


def get_exercise_history(exercise_id, user_id):
    with get_conn() as conn:
        primary_name = conn.execute(
            "SELECT primary_name FROM exercises WHERE exercise_id = ?", (exercise_id,)
        ).fetchone()[0]
        rows = conn.execute("""
            SELECT ei.instance_id, ws.date, ei.intensity, ei.workout_index, ei.notes,
                   es.weight, es.reps, es.rest_time, es.set_number
            FROM exercise_instances ei
            JOIN workout_sessions ws ON ei.workout_id = ws.workout_id
            JOIN exercise_sets es ON es.instance_id = ei.instance_id
            WHERE ei.exercise_id = ? AND ws.user_id = ?
            ORDER BY ws.date ASC, ei.instance_id ASC, es.set_number ASC
        """, (exercise_id, user_id)).fetchall()

    instances = {}
    for row in rows:
        key = (row[0], row[1], row[2], row[3], row[4])
        instances.setdefault(key, {"sets": [], "rests": []})
        instances[key]["sets"].append(f"{_fmt_weight(row[5])}x{_fmt_weight(row[6])}")
        if row[7] is not None:
            instances[key]["rests"].append(str(_fmt_weight(row[7])))

    history = []
    for (instance_id, date, intensity, workout_index, notes), data in instances.items():
        history.append({
            "date": date,
            "intensity": intensity,
            "workout_index": workout_index,
            "notes": notes,
            "sets": ", ".join(data["sets"]),
            "rest": ", ".join(data["rests"]) if data["rests"] else None,
        })

    return primary_name, history


@app.route("/")
def index():
    with get_conn() as conn:
        users = conn.execute("SELECT user_id, username FROM users ORDER BY username").fetchall()
    return render_template("index.html", users=users)


@app.route("/user/<int:user_id>")
def user_home(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return redirect(url_for("index"))
        muscle_groups = conn.execute(
            "SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group"
        ).fetchall()
    return render_template("user_home.html", user_id=user_id, username=user[0],
                           muscle_groups=[m[0] for m in muscle_groups])


@app.route("/user/<int:user_id>/muscle/<group>")
def muscle_group(user_id, group):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        exercises = conn.execute(
            "SELECT exercise_id, primary_name FROM exercises WHERE muscle_group = ? ORDER BY primary_name",
            (group,)
        ).fetchall()
    return render_template("muscle_group.html", user_id=user_id, username=user[0],
                           group=group, exercises=exercises)


@app.route("/user/<int:user_id>/exercise/<int:exercise_id>")
def exercise_history(user_id, exercise_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
    intensity_filter = request.args.get("intensity")
    primary_name, history = get_exercise_history(exercise_id, user_id)
    if intensity_filter:
        history = [h for h in history if h["intensity"] == intensity_filter]
    return render_template("exercise_history.html", user_id=user_id, username=user[0],
                           primary_name=primary_name, history=history,
                           intensity_filter=intensity_filter, exercise_id=exercise_id)


@app.route("/user/<int:user_id>/search")
def search(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        query = request.args.get("q", "").strip().lower()
        results = []
        if query:
            results = conn.execute("""
                SELECT DISTINCT e.exercise_id, e.primary_name FROM exercises e
                LEFT JOIN exercise_aliases ea ON e.exercise_id = ea.exercise_id
                WHERE e.primary_name LIKE ? OR ea.alias LIKE ?
                ORDER BY e.primary_name
            """, (f"%{query}%", f"%{query}%")).fetchall()
    return render_template("search.html", user_id=user_id, username=user[0],
                           query=query, results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
