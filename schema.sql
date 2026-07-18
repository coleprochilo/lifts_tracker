CREATE TABLE IF NOT EXISTS exercises (
    exercise_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_name  TEXT NOT NULL,
    muscle_group  TEXT,
    user_id       INTEGER REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS exercise_aliases (
    alias_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id   INTEGER NOT NULL REFERENCES exercises(exercise_id),
    alias         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    date_created  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS split_days (
    split_day_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    user_id       INTEGER REFERENCES users(user_id),
    UNIQUE(name, user_id)
);

CREATE TABLE IF NOT EXISTS workout_sessions (
    workout_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    date          TEXT NOT NULL,
    split_day     TEXT REFERENCES split_days(name),
    ended         INTEGER DEFAULT 0,
    notes         TEXT
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
    reps         REAL,
    rest_time    REAL,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS superset_instances (
    superset_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id     INTEGER NOT NULL REFERENCES workout_sessions(workout_id),
    exercise_id_a  INTEGER NOT NULL REFERENCES exercises(exercise_id),
    exercise_id_b  INTEGER NOT NULL REFERENCES exercises(exercise_id),
    intensity      TEXT,
    workout_index  INTEGER,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS superset_sets (
    superset_set_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    superset_id      INTEGER NOT NULL REFERENCES superset_instances(superset_id),
    set_number       INTEGER NOT NULL,
    weight_a         REAL,
    reps_a           REAL,
    weight_b         REAL,
    reps_b           REAL,
    rest_time        REAL,
    notes            TEXT
);
