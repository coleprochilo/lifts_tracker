# lifts_tracker — Project Notes & Decisions

## Project Overview
A personal workout tracking CLI app built in Python with a local SQLite database.
The goal is to track lifting progress so the user can see what weights/reps they did
last time and improve each session. Eventually will be expanded to a mobile app.

## User Preferences & Coding Style
- Write MINIMAL code — no verbose implementations, no unnecessary code
- Do NOT add tests unless explicitly asked
- Do NOT remove existing code unless explicitly asked
- Do NOT make changes without confirming with the user first
- Ask clarifying questions before implementing anything non-trivial
- Make all changes to the same file at once, not incrementally
- User writes casually, match that tone
- User sometimes makes typos — interpret charitably
- User's name is Cole Prochilo

---

## Tech Stack
- Python 3
- SQLite via `sqlite3` (standard library)
- `bcrypt` for password hashing
- `python-dateutil` for flexible date parsing
- No ORM — raw SQL queries

---

## File Structure
- `lifts_tracker.py` — main app, all classes and CLI logic
- `db.py` — DB connection and schema initialization
- `schema.sql` — SQLite schema
- `import_csv.py` — one-time CSV import script for historical data
- `exercise_mapping.py` — full primary name and alias mapping, seeded into DB on init
- `primary_and_aliases_mapping.txt` — reference document for exercise naming decisions
- `lifts_tracker.db` — SQLite database file (delete to reset)
- `Gym Chart.csv` — historical workout data (Jan-Apr 2026, will grow to 12 months)

---

## Database Schema

### split_days
- `split_day_id` INTEGER PK AUTOINCREMENT
- `name` TEXT UNIQUE
- Seeded with: `S/L`, `C/T`, `B/B`
- User can add new values via "Manage split days" menu option

### exercises (GLOBAL — shared across all users)
- `exercise_id` INTEGER PK AUTOINCREMENT
- `primary_name` TEXT UNIQUE

### exercise_aliases
- `alias_id` INTEGER PK AUTOINCREMENT
- `exercise_id` FK → exercises
- `alias` TEXT UNIQUE
- Separate table because one exercise has many aliases (one-to-many)
- Every entered name that maps to an exercise gets saved as an alias automatically

### users
- `user_id` INTEGER PK AUTOINCREMENT
- `username` TEXT UNIQUE (spaces allowed)
- `password_hash` TEXT
- `date_created` TEXT (YYYY-MM-DD)

### workout_sessions
- `workout_id` INTEGER PK AUTOINCREMENT
- `user_id` FK → users
- `date` TEXT (YYYY-MM-DD)
- `split_day` TEXT FK → split_days(name)

### exercise_instances (user-specific)
- `instance_id` INTEGER PK AUTOINCREMENT
- `workout_id` FK → workout_sessions
- `exercise_id` FK → exercises
- `entered_name` TEXT (raw name as typed by user)
- `intensity` TEXT (light/normal/heavy)
- `workout_index` INTEGER (order in session, entered manually)
- `notes` TEXT nullable

### exercise_sets
- `set_id` INTEGER PK AUTOINCREMENT
- `instance_id` FK → exercise_instances
- `set_number` INTEGER
- `weight` REAL
- `reps` REAL (float to support 0.5 half reps)
- `rest_time` REAL nullable (NULL on last set — only rest between sets)

---

## Key Design Decisions

### IDs
- All IDs are `INTEGER PRIMARY KEY AUTOINCREMENT` — SQLite handles generation
- UUIDs were considered but rejected — single local DB, no collision risk
- If ever moving to distributed/multi-device, switch to UUIDs at that point

### Global Exercises List
- Exercises are NOT owned by users — they are global
- Users interact with exercises only through `exercise_instances`
- This allows all users to share the same exercise library

### Lazy Session Creation
- `create_workout()` returns a pending dict `{user_id, date, split_day, workout_id: None}`
- The session row is only inserted into the DB when the FIRST exercise is logged
- If user starts a session and exits without logging anything, nothing is saved

### Exercise Resolution Flow (`_resolve_exercise`)
Order of checks:
1. Exact match on `exercises.primary_name`
2. Exact match on `exercise_aliases.alias`
3. Fuzzy match (substring check on primary names and aliases)
4. If fuzzy match found → ask "did you mean X?"
5. If confirmed → save entered name as alias, return exercise_id
6. If rejected or no match → call `_reassign_or_create()`

`_reassign_or_create()`:
- Shows existing exercises list
- Asks "which exercise should this map to? (or leave blank to create new)"
- If existing name entered → save as alias, return exercise_id
- If blank → prompt for new primary name + aliases
- Entered name is ALWAYS saved as alias for whatever exercise it maps to
- Prints "New exercise '{primary}' created." after creation

### Intensity
- Valid values: `light`, `normal`, `heavy`
- Stored as `VALID_INTENSITIES = ("light", "normal", "heavy")` tuple
- Validated at input prompt — loops until valid value entered
- On instance: intensity is per-instance, NOT per-session
  (user may mix intensities in one session e.g. heavy main lift, light accessory)
- Rep guidelines (user knowledge only, NOT enforced by app):
  - light = 12 reps
  - normal = 9-12 reps
  - heavy = 6-8 reps

### Reps
- Stored as REAL (float) to support 0.5 half reps
- User will only ever use .5 as decimal

### Weights
- Stored as REAL
- `_fmt_weight(w)` helper: returns `int` if whole number, `float` otherwise
  e.g. 225.0 → 225, 52.5 → 52.5
- Applied to both weights AND reps in all display output

### Duplicate Detection
- Sessions: warns if a session already exists for that date, asks to confirm second session
- Instances: checks for identical instance (same exercise, intensity, workout_index, sets)
  before inserting — skips silently if duplicate found
- Set comparison casts both sides to float before comparing to avoid type mismatch

### Date Handling
- All dates stored as `YYYY-MM-DD` ISO format strings
- Input accepts any natural format via `dateutil.parser.parse(dayfirst=False)`
- Blank input defaults to today's date

### Workout Index
- Entered manually by user (what number exercise it was in the session)
- Validated: must be numeric, must be unique within the session
- User wants manual entry — does not want auto-increment

### Split Days
- Stored in `split_days` table so new values persist across runs
- Default values: `S/L`, `C/T`, `B/B`
- Managed via "Manage split days" main menu option (separate from session creation)
- Prompted when starting a new session, validated against DB values

---

## CLI Flow

### Main Menu
1. Start new workout session
2. View exercise history
3. View workouts by date
4. Manage split days
q. Quit

### Starting a Session
1. Prompt date (blank = today, any format accepted)
2. Warn if session already exists for that date
3. Prompt split day (validated against split_days table)
4. Session created lazily (not saved until first exercise logged)

### Session Loop
1. Log exercise
2. Confirm session → shows summary → option to edit instance or end session

### Edit Flow (within confirm)
- User enters instance name to edit
- Old instance + sets deleted from DB
- User re-enters the whole instance from scratch
- Loops back to summary after re-entry

### View Exercise History
- Prompts exercise name (checks primary name then aliases)
- Optional intensity filter (validated against VALID_INTENSITIES)
- Shows all instances ordered by date ASC

### View Workouts by Date
- If 1 session: shows full session summary directly
- If multiple sessions: lists them with session id, split day, exercise count
- User selects one, full summary shown

---

## Input Validation
All numeric inputs loop until valid:
- workout_index: must be int, must be unique in session
- num_sets: must be int > 0
- weight: must be float >= 0
- reps: must be float > 0
- rest_time: must be float >= 0, blank accepted (None)
- exercise name: cannot be empty
- intensity: must be in VALID_INTENSITIES
- split_day: must be in split_days table
- date: must be parseable by dateutil

---

## Error Handling
- `KeyboardInterrupt` caught at top level → prints "Exited. See you next time." and exits cleanly
- `sys.exit()` used for fatal errors (wrong username/password, username exists)

---

## Exercise Mapping (`exercise_mapping.py`)
- Contains `EXERCISE_MAPPING` dict: primary name → list of aliases
- Seeded into `exercises` and `exercise_aliases` tables on every `init_db()` call
- This means wiping and re-importing always starts with the correct mapping
- Once in prod, mapping lives in DB permanently — this file is only needed for testing resets
- Naming convention for primary names (in order): position (kneeling/standing/seated) → grip (supinated/pronated/neutral) → one arm → equipment (db/bb/cable) → exercise name
- Pluralization rules: curls, rows, flys stay plural — everything else singular
- Typos from real CSV data are intentionally included as aliases so they get caught on future imports

## CSV Import (`import_csv.py`)
- Imports historical data from `Gym Chart.csv`
- CSV structure: months side by side, 9 columns per month (8 data + 1 blank separator), up to 12 months
- Column offsets: 0, 9, 18, 27 (add 9 per new month)
- Identifies lifting days by split day keyword in exercise column + valid intensity in weight column
- Skips cardio, circuit, rest days
- Multi-set weights/reps stored as comma-separated strings e.g. `"120, 127.5"`
- Rest time is repeated for all sets if only one value given
- Maps all data to user `cole prochilo`
- Uses lazy session creation (same as app)
- `resolve_exercise()` checks primary name then aliases — warns if name not found in mapping
- Re-runnable: delete `lifts_tracker.db`, register user, run script

---

## Future Plans
- Data visualization / graphing (matplotlib/pandas) — data structure already supports this
- Mobile app via React Native frontend + Flask/FastAPI Python backend
- Hosting options: AWS EC2 + SQLite (cheap, ~$8-10/month after free tier) or home server (Raspberry Pi)
- Add cardio tracking (date, distance, duration, pace, elevation)
- Add circuit tracking (global circuits list, sessions with rounds and total time)
- File-based import: user writes workouts in Notes app in a defined format, parser imports them
- When moving to prod: re-run `import_csv.py` against fresh DB to get all historical data in

---

## Known Issues / TODO
- `prompt_view_history` searches by primary name/alias only — does not do fuzzy matching
  (unlike `_resolve_exercise` which does fuzzy matching)
- No way to delete a session or exercise from the CLI yet
- No way to view all sessions (only by date)
- CSV import `MONTH_OFFSETS` needs to be updated manually as new months are added to the spreadsheet
