import sys
import bcrypt
from datetime import date
from dateutil import parser as dateparser
from db import get_conn, init_db


class User:
    """
    Represents a logged-in user. Holds user identity and provides all
    methods for interacting with the database on behalf of that user.
    """

    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

    @staticmethod
    def register(username, password):
        """
        Registers a new user and saves them to the database.

        Params:
            username (str): desired username
            password (str): plaintext password, will be hashed before storage

        Returns:
            User: a new User instance for the registered user

        Exits:
            if username already exists in the database
        """
        with get_conn() as conn:
            existing = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                sys.exit("Username already exists.")
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, password_hash, date_created) VALUES (?, ?, ?)",
                (username, password_hash, date.today().isoformat())
            )
            user_id = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()[0]
        print(f"User {username} registered successfully.")
        return User(user_id, username)

    @staticmethod
    def login(username, password):
        """
        Authenticates an existing user against the database.

        Params:
            username (str): the user's username
            password (str): plaintext password to verify against stored hash

        Returns:
            User: a User instance for the authenticated user

        Exits:
            if username or password is empty, username not found, or password is incorrect
        """
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

    def create_workout(self, date, split_day):
        """
        Creates a pending workout session dict. The session is not written
        to the database until the first exercise instance is logged (lazy creation).

        Params:
            date (str): session date in YYYY-MM-DD format
            split_day (str): the muscle split for this session (e.g. 'S/L', 'C/T', 'B/B')

        Returns:
            dict: session dict with keys user_id, date, split_day, workout_id (None until first insert)
        """
        print(f"Session ready for {date} ({split_day}) — will be saved on first exercise logged.")
        return {"user_id": self.user_id, "date": date, "split_day": split_day, "workout_id": None}

    def add_exercise_instance(self, new_instance, session):
        """
        Resolves the exercise, lazily creates the session if needed, checks for duplicates,
        then inserts the exercise instance and its sets into the database.

        Params:
            new_instance (Exercise_Instance): the instance to log
            session (dict): the current session dict, workout_id may be None on first call

        Returns:
            None. Prints recent entries for the exercise after logging.
            Skips insert and prints a message if an identical entry already exists.
        """
        exercise_id = self._resolve_exercise(new_instance.entered_name)

        with get_conn() as conn:
            if session["workout_id"] is None:
                conn.execute("INSERT INTO workout_sessions (user_id, date, split_day) VALUES (?, ?, ?)", (session["user_id"], session["date"], session["split_day"]))
                session["workout_id"] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"Session saved | id: {session['workout_id']}")

            # duplicate check
            existing = conn.execute("""
                SELECT ei.instance_id FROM exercise_instances ei
                WHERE ei.workout_id = ? AND ei.exercise_id = ? AND ei.intensity = ? AND ei.workout_index = ?
            """, (session["workout_id"], exercise_id, new_instance.intensity, new_instance.workout_index)).fetchone()
            if existing:
                instance_id = existing[0]
                existing_sets = [(float(w), float(r)) for w, r in conn.execute(
                    "SELECT weight, reps FROM exercise_sets WHERE instance_id = ? ORDER BY set_number",
                    (instance_id,)
                ).fetchall()]
                new_sets = list(zip(new_instance.weights, new_instance.reps))
                if existing_sets == new_sets:
                    print("Duplicate entry detected, skipping.")
                    return
            conn.execute(
                "INSERT INTO exercise_instances (workout_id, exercise_id, entered_name, intensity, workout_index, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (session["workout_id"], exercise_id, new_instance.entered_name, new_instance.intensity, new_instance.workout_index, new_instance.notes)
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
        """
        Resolves an entered exercise name to an exercise_id in the database.
        Checks in order: primary name → alias → fuzzy match → prompt user to reassign or create.
        Prompts user to confirm any match before accepting it.

        Params:
            name (str): the exercise name as entered by the user

        Returns:
            int: the exercise_id of the matched or newly created exercise
        """
        name = name.lower()
        with get_conn() as conn:
            # check primary name
            row = conn.execute("SELECT exercise_id, primary_name FROM exercises WHERE primary_name = ?", (name,)).fetchone()
            if row:
                print(f"'{name}' mapped to '{row[1]}', correct? (y/n)")
                if input().strip().lower() == "y":
                    return row[0]
                return self._reassign_or_create(name)
            # check aliases
            row = conn.execute("""
                SELECT e.exercise_id, e.primary_name FROM exercise_aliases ea
                JOIN exercises e ON e.exercise_id = ea.exercise_id
                WHERE ea.alias = ?
            """, (name,)).fetchone()
            if row:
                print(f"'{name}' mapped to '{row[1]}', correct? (y/n)")
                if input().strip().lower() == "y":
                    return row[0]
                return self._reassign_or_create(name)
            # fuzzy check
            all_exercises = conn.execute("SELECT exercise_id, primary_name FROM exercises").fetchall()
            all_aliases = conn.execute("SELECT exercise_id, alias FROM exercise_aliases").fetchall()

        print(f"No exercise found for '{name}'.")

        close_match = next((e for e in all_exercises if name in e[1] or e[1] in name), None)
        close_match = close_match or next((a for a in all_aliases if name in a[1] or a[1] in name), None)
        if close_match:
            print(f"Did you mean '{close_match[1]}'? (y/n)")
            if input().strip().lower() == "y":
                with get_conn() as conn:
                    conn.execute("INSERT OR IGNORE INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (close_match[0], name))
                return close_match[0]

        return self._reassign_or_create(name)

    def _reassign_or_create(self, name):
        """
        Prompts the user to either map the entered name to an existing exercise
        or create a brand new exercise with a primary name and optional aliases.
        The entered name is always saved as an alias for whichever exercise it maps to.

        Params:
            name (str): the unresolved exercise name entered by the user

        Returns:
            int: the exercise_id of the matched or newly created exercise
        """
        with get_conn() as conn:
            all_exercises = conn.execute("SELECT exercise_id, primary_name FROM exercises").fetchall()
        print("Existing exercises: " + ", ".join(e[1] for e in all_exercises))
        existing = input(f"Which exercise should '{name}' map to? (or leave blank to create new): ").strip().lower()
        with get_conn() as conn:
            if existing:
                row = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (existing,)).fetchone()
                if row:
                    conn.execute("INSERT OR IGNORE INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (row[0], name))
                    return row[0]
                print(f"'{existing}' not found, creating new exercise.")
            primary = input("Enter primary name for new exercise: ").strip().lower()
            conn.execute("INSERT INTO exercises (primary_name) VALUES (?)", (primary,))
            exercise_id = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (primary,)).fetchone()[0]
            aliases = [a.strip().lower() for a in input("Enter aliases (comma separated, or leave blank): ").split(",") if a.strip()]
            for alias in [name] + aliases:
                conn.execute("INSERT OR IGNORE INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (exercise_id, alias))
            print(f"New exercise '{primary}' created.")
        return exercise_id

    def _print_recent(self, exercise_id, entered_name, n=3):
        """
        Prints the n most recent instances of an exercise for this user.

        Params:
            exercise_id (int): the exercise to look up
            entered_name (str): the name as entered by the user, used in the header
            n (int): number of recent instances to show, defaults to 3

        Returns:
            None. Prints directly to stdout.
        """
        with get_conn() as conn:
            primary = conn.execute("SELECT primary_name FROM exercises WHERE exercise_id = ?", (exercise_id,)).fetchone()[0]
            rows = conn.execute("""
                SELECT ei.instance_id, ws.date, ei.intensity, ei.notes,
                       es.weight, es.reps, es.set_number
                FROM exercise_instances ei
                JOIN workout_sessions ws ON ei.workout_id = ws.workout_id
                JOIN exercise_sets es ON es.instance_id = ei.instance_id
                WHERE ei.exercise_id = ? AND ws.user_id = ?
                ORDER BY ws.date DESC, ei.instance_id DESC, es.set_number ASC
            """, (exercise_id, self.user_id)).fetchall()

        instances = {}
        for row in rows:
            key = (row[0], row[1], row[2], row[3])
            instances.setdefault(key, []).append(f"{_fmt_weight(row[4])}x{_fmt_weight(row[5])}")

        recent = list(instances.items())[:n]
        print(f"\n'{entered_name}' added for '{primary}'. Recent '{primary}' entries:")
        for (instance_id, date, intensity, notes), sets in reversed(recent):
            print(f"{date} | intensity: {intensity} | sets: {','.join(sets)} | notes: {notes}")

    def get_workouts_by_date(self, date):
        """
        Looks up all workout sessions for this user on a given date.
        If one session found, prints its full summary.
        If multiple sessions found, lists them and prompts the user to select one.

        Params:
            date (str): date in YYYY-MM-DD format

        Returns:
            None. Prints directly to stdout.
        """
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT workout_id, split_day FROM workout_sessions WHERE user_id = ? AND date = ?",
                (self.user_id, date)
            ).fetchall()
        if not rows:
            print(f"No workouts found for {date}")
            return
        if len(rows) == 1:
            print_session_summary({"workout_id": rows[0][0], "split_day": rows[0][1], "date": date})
        else:
            with get_conn() as conn:
                counts = {
                    r[0]: r[1] for r in conn.execute("""
                        SELECT workout_id, COUNT(*) FROM exercise_instances
                        WHERE workout_id IN ({}) GROUP BY workout_id
                    """.format(",".join("?" * len(rows))), [r[0] for r in rows]).fetchall()
                }
            for i, (workout_id, split_day) in enumerate(rows, 1):
                print(f"{i}. Session {workout_id} — {split_day} — {counts.get(workout_id, 0)} exercises")
            while True:
                try:
                    choice = int(input("\nSelect session: ").strip())
                    if 1 <= choice <= len(rows):
                        selected = rows[choice - 1]
                        print_session_summary({"workout_id": selected[0], "split_day": selected[1], "date": date})
                        break
                    print(f"Enter a number between 1 and {len(rows)}.")
                except ValueError:
                    print("Must enter a numeric value.")


def _fmt_weight(w):
    """
    Formats a numeric value by stripping unnecessary decimals.
    e.g. 225.0 -> 225, 52.5 -> 52.5

    Params:
        w (float): the value to format

    Returns:
        int or float: int if the value is whole, float otherwise
    """
    return int(w) if w == int(w) else w


VALID_INTENSITIES = ("light", "normal", "heavy")


class Exercise_Instance:
    """
    Represents a single exercise instance to be logged.
    Holds all data for one exercise performed in a session before it is written to the DB.
    """

    def __init__(self, entered_name, intensity, workout_index, notes, weights=None, reps=None, rest_times=None):
        """
        Params:
            entered_name (str): the name as typed by the user
            intensity (str): one of VALID_INTENSITIES
            workout_index (int): the order of this exercise in the session
            notes (str or None): optional notes
            weights (list of float): weight used per set
            reps (list of float): reps completed per set
            rest_times (list of float or None): rest time in minutes between sets, None for last set

        Raises:
            ValueError: if weights and reps lists are different lengths
        """
        self.entered_name = entered_name.lower()
        self.intensity = intensity
        self.workout_index = workout_index
        self.notes = notes
        self.weights = weights or []
        self.reps = reps or []
        if len(self.weights) != len(self.reps):
            raise ValueError(f"weights and reps must be the same length, got {len(self.weights)} and {len(self.reps)}")
        self.rest_times = rest_times or []


def prompt_log_exercise(user, session):
    """
    Interactive CLI prompt to collect all data for a new exercise instance
    and log it to the current session.

    Params:
        user (User): the logged-in user
        session (dict): the current session dict

    Returns:
        None. Calls user.add_exercise_instance() with the collected data.
    """
    while True:
        name = input("Exercise name: ").strip()
        if name:
            break
        print("Exercise name cannot be empty.")

    while True:
        intensity = input(f"Intensity ({'/'.join(VALID_INTENSITIES)}): ").strip().lower()
        if intensity in VALID_INTENSITIES:
            break
        print(f"Invalid intensity, choose from {', '.join(VALID_INTENSITIES)}")

    while True:
        try:
            workout_index = int(input("Exercise number in workout: ").strip())
        except ValueError:
            print("Must enter a numeric value.")
            continue
        with get_conn() as conn:
            taken = conn.execute(
                "SELECT 1 FROM exercise_instances WHERE workout_id = ? AND workout_index = ?",
                (session["workout_id"], workout_index)
            ).fetchone() if session["workout_id"] else None
        if taken:
            print(f"#{workout_index} is already taken in this session, enter a different number.")
        else:
            break

    while True:
        try:
            num_sets = int(input("How many sets: ").strip())
            if num_sets <= 0:
                print("Must enter at least 1 set.")
            else:
                break
        except ValueError:
            print("Must enter a numeric value.")

    weights, reps, rest_times = [], [], []
    for i in range(num_sets):
        print(f"\n  Set {i + 1}")
        while True:
            try:
                w = float(input("    Weight: ").strip())
                if w < 0:
                    print("Weight cannot be negative.")
                else:
                    break
            except ValueError:
                print("Must enter a numeric value.")
        weights.append(w)
        while True:
            try:
                r = float(input("    Reps: ").strip())
                if r <= 0:
                    print("Reps must be greater than 0.")
                else:
                    break
            except ValueError:
                print("Must enter a numeric value.")
        reps.append(r)
        if i < num_sets - 1:
            while True:
                rest = input("    Rest time (mins): ").strip()
                if not rest:
                    rest_times.append(None)
                    break
                try:
                    rest_val = float(rest)
                    if rest_val < 0:
                        print("Rest time cannot be negative.")
                    else:
                        rest_times.append(rest_val)
                        break
                except ValueError:
                    print("Must enter a numeric value.")

    notes = input("\nNotes (or leave blank): ").strip() or None

    instance = Exercise_Instance(name, intensity, workout_index, notes, weights, reps, rest_times)
    user.add_exercise_instance(instance, session)


def prompt_view_history(user):
    """
    Interactive CLI prompt to view the full history of an exercise for the logged-in user,
    with an optional intensity filter.

    Params:
        user (User): the logged-in user

    Returns:
        None. Prints exercise history directly to stdout.
    """
    name = input("Exercise name: ").strip().lower()
    with get_conn() as conn:
        row = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ?", (name,)).fetchone()
        if not row:
            row = conn.execute("SELECT exercise_id FROM exercise_aliases WHERE alias = ?", (name,)).fetchone()
        if not row:
            print(f"No exercise found for '{name}'")
            return
        exercise_id = row[0]
        filter_intensity = input("Filter by intensity (leave blank for all): ").strip().lower() or None
        if filter_intensity:
            while filter_intensity not in VALID_INTENSITIES:
                print(f"Invalid intensity, choose from {', '.join(VALID_INTENSITIES)} or leave blank for all.")
                filter_intensity = input("Filter by intensity: ").strip().lower() or None
                if not filter_intensity:
                    break
        query = """
            SELECT ei.instance_id, ws.date, ei.intensity, ei.workout_index, ei.notes,
                   es.weight, es.reps, es.set_number
            FROM exercise_instances ei
            JOIN workout_sessions ws ON ei.workout_id = ws.workout_id
            JOIN exercise_sets es ON es.instance_id = ei.instance_id
            WHERE ei.exercise_id = ? AND ws.user_id = ?
        """
        params = [exercise_id, user.user_id]
        if filter_intensity:
            query += " AND ei.intensity = ?"
            params.append(filter_intensity)
        query += " ORDER BY ws.date ASC, ei.instance_id ASC, es.set_number ASC"
        rows = conn.execute(query, params).fetchall()
    if not rows:
        print("No history found.")
        return
    instances = {}
    for row in rows:
        key = (row[0], row[1], row[2], row[3], row[4])
        instances.setdefault(key, []).append(f"{_fmt_weight(row[5])}x{_fmt_weight(row[6])}")
    print(f"\n--- {name} history ---")
    for (instance_id, date, intensity, workout_index, notes), sets in instances.items():
        print(f"{date} | #{workout_index} | {intensity} | {','.join(sets)} | notes: {notes}")


def print_session_summary(session):
    """
    Prints a formatted summary of all exercise instances in a session,
    ordered by workout_index.

    Params:
        session (dict): must contain workout_id, date, and split_day

    Returns:
        None. Prints directly to stdout.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT ei.instance_id, ei.entered_name, ei.intensity, ei.workout_index, ei.notes,
                   es.weight, es.reps, es.set_number
            FROM exercise_instances ei
            JOIN exercise_sets es ON es.instance_id = ei.instance_id
            WHERE ei.workout_id = ?
            ORDER BY ei.workout_index ASC, es.set_number ASC
        """, (session["workout_id"],)).fetchall()
    instances = {}
    for row in rows:
        key = (row[0], row[1], row[2], row[3], row[4])
        instances.setdefault(key, []).append(f"{_fmt_weight(row[5])}x{_fmt_weight(row[6])}")
    print("\n--- Session Summary ---")
    print(f"Date: {session['date']} | Split: {session['split_day']}")
    for (instance_id, entered_name, intensity, workout_index, notes), sets in instances.items():
        print(f"  #{workout_index} {entered_name} | {intensity} | {','.join(sets)} | notes: {notes}")
    print("-----------------------")


def session_loop(user, session):
    """
    Inner loop for an active workout session. Allows the user to log exercises
    or confirm/end the session. On confirm, shows a summary and allows editing
    any instance before finalizing.

    Params:
        user (User): the logged-in user
        session (dict): the current session dict

    Returns:
        None.
    """
    while True:
        print("\n1. Log exercise\n2. Confirm session")
        choice = input("\n> ").strip()
        if choice == "1":
            prompt_log_exercise(user, session)
        elif choice == "2":
            if session["workout_id"] is None:
                print("No exercises logged, session discarded.")
                break
            while True:
                print_session_summary(session)
                print("\n1. Edit an instance\n2. End session")
                confirm_choice = input("\n> ").strip()
                if confirm_choice == "1":
                    edit_name = input("Enter instance name to edit: ").strip().lower()
                    with get_conn() as conn:
                        row = conn.execute("""
                            SELECT ei.instance_id FROM exercise_instances ei
                            WHERE ei.workout_id = ? AND ei.entered_name = ?
                        """, (session["workout_id"], edit_name)).fetchone()
                    if not row:
                        print(f"No instance found for '{edit_name}' in this session.")
                        continue
                    with get_conn() as conn:
                        conn.execute("DELETE FROM exercise_sets WHERE instance_id = ?", (row[0],))
                        conn.execute("DELETE FROM exercise_instances WHERE instance_id = ?", (row[0],))
                    print(f"'{edit_name}' removed. Re-enter it now:")
                    prompt_log_exercise(user, session)
                elif confirm_choice == "2":
                    print("Session ended. Good work.")
                    break
            break


def manage_split_days():
    """
    Displays the current list of valid split days and allows the user to add a new one.
    New values are persisted to the split_days table in the database.

    Params:
        None

    Returns:
        None. Prints current split days and confirmation of any addition.
    """
    with get_conn() as conn:
        splits = [r[0] for r in conn.execute("SELECT name FROM split_days").fetchall()]
    print("\nCurrent split days: " + ", ".join(splits))
    new = input("Enter new split day to add (or leave blank to cancel): ").strip()
    if new:
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO split_days (name) VALUES (?)", (new,))
        print(f"'{new}' added.")


def main_loop(user):
    """
    Main menu loop for the application. Presents options to start a session,
    view history, look up workouts by date, manage split days, or quit.

    Params:
        user (User): the logged-in user

    Returns:
        None.
    """
    print(f"\n{'='*50}\n         LIFTS TRACKER - Welcome, {user.username}\n{'='*50}")
    while True:
        print("\n1. Start new workout session\n2. View exercise history\n3. View workouts by date\n4. Manage split days\nq. Quit")
        choice = input("\n> ").strip().lower()
        if choice == "1":
            while True:
                date_input = input("Session date (leave blank for today): ").strip()
                if not date_input:
                    session_date = date.today().isoformat()
                else:
                    try:
                        session_date = dateparser.parse(date_input, dayfirst=False).date().isoformat()
                    except ValueError:
                        print("Couldn't parse that date, try again.")
                        continue
                with get_conn() as conn:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM workout_sessions WHERE user_id = ? AND date = ?",
                        (user.user_id, session_date)
                    ).fetchone()[0]
                if count:
                    print(f"There is already {count} session(s) for {session_date}. Start another? (y/n)")
                    if input().strip().lower() != "y":
                        continue
                break
            with get_conn() as conn:
                valid_splits = [r[0] for r in conn.execute("SELECT name FROM split_days").fetchall()]
            while True:
                split_day = input(f"Split day ({', '.join(valid_splits)}): ").strip()
                if split_day in valid_splits:
                    break
                print(f"Invalid split day, choose from {', '.join(valid_splits)}")
            session = user.create_workout(session_date, split_day)
            session_loop(user, session)
        elif choice == "2":
            prompt_view_history(user)
        elif choice == "3":
            date_input = input("Date: ").strip()
            try:
                parsed = dateparser.parse(date_input, dayfirst=False).date().isoformat()
            except ValueError:
                print("Couldn't parse that date, try again.")
                continue
            user.get_workouts_by_date(parsed)
        elif choice == "4":
            manage_split_days()
        elif choice == "q":
            print("See you next time.")
            break


if __name__ == "__main__":
    try:
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
        main_loop(user)
    except KeyboardInterrupt:
        print("\nExited. See you next time.")
