from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_conn
from datetime import date
import hashlib

app = Flask(__name__)
app.secret_key = "lifts-tracker-secret"


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


@app.route("/user/<int:user_id>/login", methods=["GET", "POST"])
def login(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username, password_hash FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        if hashlib.sha256(request.form.get("password", "").encode()).hexdigest() == user[1]:
            return redirect(url_for("user_home", user_id=user_id))
        error = "Wrong password, try again."
    return render_template("login.html", user_id=user_id, username=user[0], error=error)


@app.route("/user/<int:user_id>")
def user_home(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return redirect(url_for("index"))
        muscle_groups = conn.execute(
            "SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group"
        ).fetchall()
        today = request.args.get("local_date") or date.today().isoformat()
        today_session = conn.execute(
            "SELECT workout_id, split_day FROM workout_sessions WHERE user_id = ? AND date = ? ORDER BY workout_id DESC LIMIT 1",
            (user_id, today)
        ).fetchone()
        latest_session = conn.execute(
            "SELECT workout_id, date, split_day FROM workout_sessions WHERE user_id = ? AND workout_id != ? ORDER BY workout_id DESC LIMIT 1",
            (user_id, today_session[0] if today_session else -1)
        ).fetchone()
        latest_split_session = conn.execute(
            "SELECT workout_id, date, split_day FROM workout_sessions WHERE user_id = ? AND split_day = ? AND workout_id != ? ORDER BY workout_id DESC LIMIT 1",
            (user_id, today_session[1], today_session[0])
        ).fetchone() if today_session else None
    return render_template("user_home.html", user_id=user_id, username=user[0],
                           muscle_groups=[m[0] for m in muscle_groups],
                           today_session=today_session, today=today,
                           latest_session=latest_session, latest_split_session=latest_split_session)


@app.route("/user/<int:user_id>/muscle/<group>/new", methods=["GET", "POST"])
def create_exercise(user_id, group):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return redirect(url_for("index"))
        muscle_groups = [r[0] for r in conn.execute("SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group").fetchall()]
        if request.method == "POST":
            primary_name = request.form.get("primary_name", "").strip()
            muscle_group = request.form.get("muscle_group", "").strip()
            if primary_name and muscle_group:
                conn.execute("INSERT OR IGNORE INTO exercises (primary_name, muscle_group) VALUES (?, ?)", (primary_name, muscle_group))
            return redirect(url_for("muscle_group", user_id=user_id, group=muscle_group or group))
    return render_template("create_exercise.html", user_id=user_id, username=user[0],
                           group=group, muscle_groups=muscle_groups)


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
        latest_session = conn.execute(
            "SELECT workout_id, date FROM workout_sessions WHERE user_id = ? ORDER BY workout_id DESC LIMIT 1",
            (user_id,)
        ).fetchone()
    intensity_filter = request.args.get("intensity")
    primary_name, history = get_exercise_history(exercise_id, user_id)
    if intensity_filter:
        history = [h for h in history if h["intensity"] == intensity_filter]
    return render_template("exercise_history.html", user_id=user_id, username=user[0],
                           primary_name=primary_name, history=history,
                           intensity_filter=intensity_filter, exercise_id=exercise_id,
                           latest_session_date=latest_session[1] if latest_session else None,
                           latest_session_id=latest_session[0] if latest_session else None)


def get_today_session(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT workout_id FROM workout_sessions WHERE user_id = ? AND date = ?",
            (user_id, date.today().isoformat())
        ).fetchone()


@app.route("/user/<int:user_id>/session/<int:workout_id>")
def session_detail(user_id, workout_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        session = conn.execute(
            "SELECT workout_id, date, split_day FROM workout_sessions WHERE workout_id = ? AND user_id = ?",
            (workout_id, user_id)
        ).fetchone()
        if not user or not session:
            return redirect(url_for("user_home", user_id=user_id))
        instances = conn.execute("""
            SELECT ei.workout_index, e.primary_name, ei.intensity, ei.notes, ei.instance_id
            FROM exercise_instances ei
            JOIN exercises e ON ei.exercise_id = e.exercise_id
            WHERE ei.workout_id = ?
            ORDER BY ei.workout_index
        """, (workout_id,)).fetchall()
        instance_sets = {}
        for inst in instances:
            sets = conn.execute(
                "SELECT weight, reps, rest_time FROM exercise_sets WHERE instance_id = ? ORDER BY set_number",
                (inst[4],)
            ).fetchall()
            def fmt(v):
                return int(v) if v == int(v) else v
            instance_sets[inst[4]] = {
                "sets_str": ", ".join(f"{fmt(s[0])}x{fmt(s[1])}" for s in sets),
                "rest_str": ", ".join(str(fmt(s[2])) for s in sets[:-1] if s[2] is not None) or None
            }
    return render_template("session_detail.html", user_id=user_id, username=user[0],
                           session=session, instances=instances, instance_sets=instance_sets)


@app.route("/create-user", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        splits = request.form.getlist("splits")
        if not username or password != confirm:
            return render_template("create_user.html", splits=splits)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with get_conn() as conn:
            conn.execute("INSERT INTO users (username, password_hash, date_created) VALUES (?, ?, ?)",
                         (username, password_hash, date.today().isoformat()))
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for s in splits:
                s = s.strip()
                if s:
                    conn.execute("INSERT OR IGNORE INTO split_days (name, user_id) VALUES (?, ?)", (s, user_id))
        return redirect(url_for("user_home", user_id=user_id))
    return render_template("create_user.html")


@app.route("/user/<int:user_id>/split/add", methods=["GET", "POST"])
def add_split_day(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return redirect(url_for("index"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if name:
                conn.execute("INSERT OR IGNORE INTO split_days (name, user_id) VALUES (?, ?)", (name, user_id))
            return redirect(url_for("user_home", user_id=user_id))
        splits = [r[0] for r in conn.execute("SELECT name FROM split_days WHERE user_id = ? ORDER BY name", (user_id,)).fetchall()]
    return render_template("add_split_day.html", user_id=user_id, username=user[0], splits=splits)


@app.route("/user/<int:user_id>/session/create", methods=["GET", "POST"])
def create_session(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return redirect(url_for("index"))
        if request.method == "POST":
            split_day = request.form.get("split_day", "").strip()
            local_date = request.form.get("local_date", "").strip() or date.today().isoformat()
            if split_day:
                conn.execute(
                    "INSERT INTO workout_sessions (user_id, date, split_day) VALUES (?, ?, ?)",
                    (user_id, local_date, split_day)
                )
            return redirect(url_for("user_home", user_id=user_id, local_date=local_date))
        split_days = conn.execute("SELECT name FROM split_days WHERE user_id = ? ORDER BY name", (user_id,)).fetchall()
    return render_template("create_session.html", user_id=user_id, username=user[0],
                           split_days=[s[0] for s in split_days])


@app.route("/user/<int:user_id>/exercise/<int:exercise_id>/log", methods=["GET", "POST"])
def log_instance(user_id, exercise_id):
    with get_conn() as conn:
        user = conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return redirect(url_for("index"))
        local_date = request.form.get("local_date", "").strip() if request.method == "POST" else request.args.get("local_date", "").strip()
        local_date = local_date or date.today().isoformat()
        session = conn.execute(
            "SELECT workout_id FROM workout_sessions WHERE user_id = ? AND date = ? ORDER BY workout_id DESC LIMIT 1",
            (user_id, local_date)
        ).fetchone()
        if not session:
            flash("No active session for today. Create a session first.")
            return redirect(url_for("exercise_history", user_id=user_id, exercise_id=exercise_id))
        workout_id = session[0]
        exercise = conn.execute("SELECT primary_name, muscle_group FROM exercises WHERE exercise_id = ?", (exercise_id,)).fetchone()
        if not exercise:
            return redirect(url_for("user_home", user_id=user_id))

        if request.method == "POST":
            intensity = request.form.get("intensity", "").strip() or None
            notes = request.form.get("notes", "").strip() or None
            local_date = request.form.get("local_date", "").strip() or date.today().isoformat()
            session = conn.execute(
                "SELECT workout_id FROM workout_sessions WHERE user_id = ? AND date = ? ORDER BY workout_id DESC LIMIT 1",
                (user_id, local_date)
            ).fetchone()
            if not session:
                return redirect(url_for("exercise_history", user_id=user_id, exercise_id=exercise_id))
            workout_id = session[0]
            weights = request.form.getlist("weight")
            reps = request.form.getlist("reps")
            rests = request.form.getlist("rest")
            sets = []
            for i, (w, r) in enumerate(zip(weights, reps)):
                try:
                    weight = float(w)
                    rep = float(r)
                except ValueError:
                    continue
                rest = None
                if i < len(rests) - 1:
                    try:
                        rest = float(rests[i]) if rests[i].strip() else None
                    except ValueError:
                        rest = None
                sets.append((weight, rep, rest))
            if sets:
                workout_index = (conn.execute(
                    "SELECT COUNT(*) FROM exercise_instances WHERE workout_id = ?", (workout_id,)
                ).fetchone()[0] or 0) + 1
                conn.execute(
                    "INSERT INTO exercise_instances (workout_id, exercise_id, entered_name, intensity, workout_index, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (workout_id, exercise_id, exercise[0], intensity, workout_index, notes)
                )
                instance_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                for set_num, (weight, rep, rest) in enumerate(sets, 1):
                    conn.execute(
                        "INSERT INTO exercise_sets (instance_id, set_number, weight, reps, rest_time) VALUES (?, ?, ?, ?, ?)",
                        (instance_id, set_num, weight, rep, rest)
                    )
            return redirect(url_for("user_home", user_id=user_id))

    return render_template("log_instance.html", user_id=user_id, username=user[0],
                           exercise_id=exercise_id, primary_name=exercise[0],
                           muscle_group=exercise[1], local_date=local_date,
                           history=get_exercise_history(exercise_id, user_id)[1][-8:])


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
