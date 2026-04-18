CREATE TABLE IF NOT EXISTS exercises (
    exercise_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS exercise_aliases (
    alias_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id   INTEGER NOT NULL REFERENCES exercises(exercise_id),
    alias         TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    date_created  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workout_sessions (
    workout_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    date          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exercise_instances (
    instance_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id     INTEGER NOT NULL REFERENCES workout_sessions(workout_id),
    exercise_id    INTEGER NOT NULL REFERENCES exercises(exercise_id),
    entered_name   TEXT NOT NULL,
    intensity      TEXT,
    workout_index  INTEGER,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS exercise_sets (
    set_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id  INTEGER NOT NULL REFERENCES exercise_instances(instance_id),
    set_number   INTEGER NOT NULL,
    weight       REAL,
    reps         INTEGER,
    rest_time    REAL
);
