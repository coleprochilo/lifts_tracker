import csv
from datetime import datetime
from db import get_conn, init_db
from exercise_mapping import EXERCISE_MAPPING, VALID_MUSCLE_GROUPS

CSV_PATH = "Gym Chart.csv"
USERNAME = "cole prochilo"
VALID_SPLITS = {"B/B Day", "C/T Day", "S/L Day", "Compounds Day"}
VALID_INTENSITIES = {"light", "normal", "heavy"}


def parse_date(raw):
    raw = raw.strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_sets(weights_raw, reps_raw, rest_raw):
    weights = [w.strip().lower().replace("bw", "0") for w in weights_raw.split(",") if w.strip()]
    reps = [r.strip().lower().replace("bw", "0") for r in reps_raw.split(",") if r.strip()]
    rest_parts = [r.strip() for r in rest_raw.split(",") if r.strip() and r.strip().upper() != "N/A"] if rest_raw.strip() else []

    if not weights or not reps or len(weights) != len(reps):
        return None

    sets = []
    for i, (w, r) in enumerate(zip(weights, reps)):
        try:
            weight = float(w)
            rep = float(r)
        except ValueError:
            return None
        rest = None
        if i < len(weights) - 1:
            if i < len(rest_parts):
                try:
                    rest = float(rest_parts[i])
                except ValueError:
                    rest = None
            elif rest_parts:
                try:
                    rest = float(rest_parts[0])
                except ValueError:
                    rest = None
        sets.append((weight, rep, rest))
    return sets


def _prompt_muscle_group():
    while True:
        mg = input(f"Muscle group ({'/'.join(VALID_MUSCLE_GROUPS)}): ").strip().lower()
        if mg in VALID_MUSCLE_GROUPS:
            return mg
        print(f"Invalid, choose from {', '.join(VALID_MUSCLE_GROUPS)}")


def get_month_offsets(rows):
    if not rows:
        return []
    header = rows[0]
    return [i for i, cell in enumerate(header) if cell.strip() == "Date"]


def get_user_id(conn):
    row = conn.execute("SELECT user_id FROM users WHERE username = ?", (USERNAME,)).fetchone()
    if not row:
        raise ValueError(f"User '{USERNAME}' not found in DB. Please register first.")
    return row[0]


def resolve_exercise(conn, name, user_id):
    name = name.lower().strip()
    row = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ? AND user_id = ?", (name, user_id)).fetchone()
    if row:
        return row[0]
    row = conn.execute("SELECT ea.exercise_id FROM exercise_aliases ea JOIN exercises e ON e.exercise_id = ea.exercise_id WHERE ea.alias = ? AND e.user_id = ?", (name, user_id)).fetchone()
    if row:
        return row[0]

    # not found — prompt user
    all_exercises = conn.execute("SELECT primary_name, muscle_group FROM exercises WHERE user_id = ? ORDER BY muscle_group, primary_name", (user_id,)).fetchall()
    current_group = None
    for primary, muscle_group in all_exercises:
        if muscle_group != current_group:
            current_group = muscle_group
            print(f"  [{muscle_group}]")
        print(f"    {primary}")
    print(f"\n'{name}' not found. All exercises:")

    choice = input("\n[n] new exercise  [a] add as alias: ").strip().lower().replace("\r", "")
    if choice == "a":
        primary = input("Primary name to alias to: ").strip().lower().replace("\r", "")
        row = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ? AND user_id = ?", (primary, user_id)).fetchone()
        if not row:
            print(f"'{primary}' not found, creating '{name}' as new primary instead.")
            muscle_group = _prompt_muscle_group()
            conn.execute("INSERT INTO exercises (primary_name, muscle_group, user_id) VALUES (?, ?, ?)", (name, muscle_group, user_id))
            return conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ? AND user_id = ?", (name, user_id)).fetchone()[0]
        conn.execute("INSERT INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (row[0], name))
        print(f"Alias '{name}' added to primary '{primary}'.")
        return row[0]
    else:
        primary = input("Primary name for new exercise: ").strip().lower().replace("\r", "")
        muscle_group = _prompt_muscle_group()
        conn.execute("INSERT INTO exercises (primary_name, muscle_group, user_id) VALUES (?, ?, ?)", (primary, muscle_group, user_id))
        exercise_id = conn.execute("SELECT exercise_id FROM exercises WHERE primary_name = ? AND user_id = ?", (primary, user_id)).fetchone()[0]
        if primary != name:
            conn.execute("INSERT INTO exercise_aliases (exercise_id, alias) VALUES (?, ?)", (exercise_id, name))
            print(f"New primary exercise added: '{primary}'. '{name}' saved as alias.")
        else:
            print(f"New primary exercise added: '{primary}'.")
        return exercise_id


def import_csv():
    init_db()

    with get_conn() as conn:
        user_id = get_user_id(conn)

    with open(CSV_PATH, newline=None, encoding="latin-1") as f:
        rows = list(csv.reader(f))

    month_offsets = get_month_offsets(rows)
    if not month_offsets:
        print("No month data found in CSV.")
        return

    sessions_imported = 0
    instances_imported = 0

    for offset in month_offsets:
        current_date = None
        current_split = None
        current_intensity = None
        workout_id = None
        workout_index = 0

        for row in rows:
            # pad row to avoid index errors
            while len(row) <= offset + 7:
                row.append("")

            date_cell = row[offset + 0].strip()
            exercise_cell = row[offset + 2].strip()
            weight_cell = row[offset + 3].strip()
            reps_cell = row[offset + 4].strip()
            rest_cell = row[offset + 5].strip()
            notes_cell = row[offset + 7].strip()

            # check if this is a new date row
            parsed_date = parse_date(date_cell) if date_cell else None
            if parsed_date:
                current_date = parsed_date
                workout_id = None
                workout_index = 0
                current_split = "misc"
                current_intensity = None

            # check if this row is a workout header (split day + intensity)
            if exercise_cell in VALID_SPLITS:
                intensity = weight_cell.strip().lower()
                current_split = exercise_cell.replace(" Day", "")
                current_intensity = intensity if intensity in VALID_INTENSITIES else None
                continue

            # skip if we don't have a valid lifting session context
            if not current_date:
                continue

            # skip empty exercise rows
            if not exercise_cell or not weight_cell or not reps_cell:
                continue

            # skip rows that look like cardio/circuit (no numeric weight)
            sets = parse_sets(weight_cell, reps_cell, rest_cell)
            if not sets:
                continue

            # we have a valid exercise instance
            with get_conn() as conn:
                # lazily create session
                if workout_id is None:
                    existing_session = conn.execute(
                        "SELECT workout_id FROM workout_sessions WHERE user_id = ? AND date = ? AND split_day = ?",
                        (user_id, current_date, current_split)
                    ).fetchone()
                    if existing_session:
                        workout_id = existing_session[0]
                    else:
                        conn.execute(
                            "INSERT INTO workout_sessions (user_id, date, split_day) VALUES (?, ?, ?)",
                            (user_id, current_date, current_split)
                        )
                        workout_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        sessions_imported += 1

                exercise_id = resolve_exercise(conn, exercise_cell, user_id)
                workout_index += 1
                notes = None

                existing_instance = conn.execute("""
                    SELECT ei.instance_id FROM exercise_instances ei
                    WHERE ei.workout_id = ? AND ei.exercise_id = ? AND ei.workout_index = ?
                """, (workout_id, exercise_id, workout_index)).fetchone()
                if existing_instance:
                    continue

                conn.execute(
                    "INSERT INTO exercise_instances (workout_id, exercise_id, entered_name, intensity, workout_index, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (workout_id, exercise_id, exercise_cell.lower(), current_intensity, workout_index, notes)
                )
                instance_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                for set_num, (weight, reps, rest) in enumerate(sets, 1):
                    conn.execute(
                        "INSERT INTO exercise_sets (instance_id, set_number, weight, reps, rest_time) VALUES (?, ?, ?, ?, ?)",
                        (instance_id, set_num, weight, reps, rest)
                    )

                instances_imported += 1

    print(f"Import complete: {sessions_imported} sessions, {instances_imported} exercise instances.")


if __name__ == "__main__":
    import subprocess, os
    key = os.path.expanduser("~/.ssh/lifts-tracker-key.pem")
    ec2 = "ec2-user@54.85.25.6"
    db_path = "lifts_tracker.db"

    print("\n⚠️  You are about to import from the CSV into the EC2 database.")
    print("    EC2 is the source of truth. The DB will be pulled from EC2 first.")
    print("    Only NEW sessions/instances from the CSV will be added — nothing will be overwritten.")
    c1 = input("\nAre you sure you want to proceed? (yes/no): ").strip().lower()
    if c1 != "yes":
        print("Import cancelled.")
        exit(0)

    c2 = input("\nDouble check: any sessions you logged through the app will NOT be deleted. Type 'confirmed' to continue: ").strip().lower()
    if c2 != "confirmed":
        print("Import cancelled.")
        exit(0)

    print("\nPulling DB from EC2...")
    pull = subprocess.run([
        "scp", "-i", key,
        f"{ec2}:~/app/{db_path}",
        db_path
    ], capture_output=True, text=True)
    if pull.returncode != 0:
        print(f"Import aborted — could not pull DB from EC2: {pull.stderr}")
        exit(1)
    print("DB pulled successfully.")

    import_csv()

    print("Pushing DB to EC2...")
    push = subprocess.run([
        "scp", "-i", key,
        db_path,
        f"{ec2}:~/app/{db_path}"
    ], capture_output=True, text=True)
    if push.returncode == 0:
        print("DB pushed to EC2 successfully.")
    else:
        print(f"DB push failed: {push.stderr}")
