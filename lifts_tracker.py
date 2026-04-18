import sys
import bcrypt
from db import get_conn, init_db


class User:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

    @staticmethod
    def register(username, password):
        with get_conn() as conn:
            existing = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                sys.exit("Username already exists.")
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            from datetime import date
            conn.execute(
                "INSERT INTO users (username, password_hash, date_created) VALUES (?, ?, ?)",
                (username, password_hash, date.today().isoformat())
            )
            user_id = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()[0]
        print(f"User {username} registered successfully.")
        return User(user_id, username)

    @staticmethod
    def login(username, password):
        if not username or not password:
            sys.exit("Username or password is empty.")
        with get_conn() as conn:
            row = conn.execute("SELECT user_id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            sys.exit("Username not found.")
        if not bcrypt.checkpw(password.encode(), row[1].encode()):
            sys.exit("Wrong password dumb bitch.")
        print(":P You're In :p")
        return User(row[0], username)

    def create_workout(self, date):
        with get_conn() as conn:
            conn.execute("INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)", (self.user_id, date))
            workout_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        print(f"New workout session created for {date} | id: {workout_id}")
        return workout_id

    def add_exercise_instance(self, new_instance, workout_id):
        exercise_id = self._resolve_exercise(new_instance.entered_name)

        with get_conn() as conn:
            conn.execute(
                "INSERT INTO exercise_instances (workout_id, exercise_id, entered_name, intensity, workout_index, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (workout_id, exercise_id, new_instance.entered_name, new_instance.intensity, new_instance.workout_index, new_instance.notes)
            )
            instance_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for i, (w, r) in enumerate(zip(new_instance.weights, new_instance.reps)):
                rest = new_instance.rest_times[i] if i < len(new_instance.rest_times) else None
                conn.execute(
                    "INSERT INTO exercise_sets (instance_id, set_number, weight, reps, rest_time) VALUES (?, ?, ?, ?, ?)",
                    (instance_id, i + 1, w, r, rest)
                )

        self._print_recent(exercise_id, new_instance.entered_name)

    def _resolve_exercise(self, name):
        name = name.lower()
        with get_conn() as conn:
            # check primary name
            row = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (name,)).fetchone()
            if row:
                return row[0]
            # check aliases
            row = conn.execute("SELECT exercise_id FROM exercise_aliases WHERE alias = ?", (name,)).fetchone()
            if row:
                return row[0]
            # fuzzy check
            all_exercises = conn.execute("SELECT exercise_id, primary_name FROM exercises").fetchall()
            all_aliases = conn.execute("SELECT exercise_id, alias FROM exercise_aliases").fetchall()

        print(f"No exercise found for '{name}'.")
        print("Existing exercises: " + ", ".join(e[1] for e in all_exercises))

        close_match = next((e for e in all_exercises if name in e[1] or e[1] in name), None)
        close_match = close_match or next((a for a in all_aliases if name in a[1] or a[1] in name), None)
        if close_match:
            print(f"Did you mean '{close_match[1]}'? (y/n)")
            if input().strip().lower() == "y":
                return close_match[0]

        existing = input("Enter existing primary name to link as alias, or leave blank to create new exercise: ").strip().lower()
        with get_conn() as conn:
            if existing:
                row = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (existing,)).fetchone()
                if row:
                    conn.execute("INSERT OR IGNORE INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (row[0], name))
                    return row[0]
            primary = input("Enter primary name for new exercise: ").strip().lower()
            conn.execute("INSERT INTO exercises (primary_name) VALUES (?)", (primary,))
            exercise_id = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (primary,)).fetchone()[0]
            aliases = [a.strip().lower() for a in input("Enter aliases (comma separated, or leave blank): ").split(",") if a.strip()]
            for alias in aliases:
                conn.execute("INSERT OR IGNORE INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (exercise_id, alias))
        return exercise_id

    def _print_recent(self, exercise_id, entered_name, n=3):
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT ei.instance_id, ws.date, ei.intensity, ei.notes,
                       GROUP_CONCAT(es.weight || 'x' || es.reps ORDER BY es.set_number) as sets
                FROM exercise_instances ei
                JOIN workout_sessions ws ON ei.workout_id = ws.workout_id
                JOIN exercise_sets es ON es.instance_id = ei.instance_id
                WHERE ei.exercise_id = ? AND ws.user_id = ?
                GROUP BY ei.instance_id
                ORDER BY ws.date DESC
                LIMIT ?
            """, (exercise_id, self.user_id, n)).fetchall()
        print(f"\n{entered_name} added. Recent entries:")
        for row in reversed(rows):
            print(f"{row[1]} | intensity: {row[2]} | sets: {row[4]} | notes: {row[3]}")

    def get_workouts_by_date(self, date):
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT workout_id FROM workout_sessions WHERE user_id = ? AND date = ?",
                (self.user_id, date)
            ).fetchall()
        if not rows:
            print(f"No workouts found for {date}")
            return
        for row in rows:
            print(f"workout_id: {row[0]}")


class Exercise_Instance:
    def __init__(self, entered_name, intensity, workout_index, notes, weights=None, reps=None, rest_times=None):
        self.entered_name = entered_name.lower()
        self.intensity = intensity
        self.workout_index = workout_index
        self.notes = notes
        self.weights = weights or []
        self.reps = reps or []
        if len(self.weights) != len(self.reps):
            raise ValueError(f"weights and reps must be the same length, got {len(self.weights)} and {len(self.reps)}")
        self.rest_times = rest_times or []


if __name__ == "__main__":
    init_db()
    print(" -------------------- Create new user or login -------------------- \n")
    create_or_login = input("Type create to create new user, type login to login with existing user\n").lower()
    if create_or_login == "create":
        user = User.register(input("Username: "), input("Password: "))
    elif create_or_login == "login":
        user = User.login(input("Username: "), input("Password: "))
    else:
        print("I said enter create or login, what else did your dumbass type\n")
        sys.exit()
    print(" -------------------- Write down ur lifts freak -------------------- \n")
