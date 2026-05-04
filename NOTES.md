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
- `matplotlib` for data visualization
- No ORM — raw SQL queries

---

## File Structure
- `lifts_tracker.py` — main app, all classes and CLI logic
- `db.py` — DB connection and schema initialization
- `schema.sql` — SQLite schema
- `graphs.py` — all graphing logic, called from main app
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
- `muscle_group` TEXT — one of `legs`, `back`, `chest`, `shoulders`, `biceps`, `triceps`

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
- Default values: `S/L`, `C/T`, `B/B`, `misc`
- `misc` added for workouts that don't fit a regular split (e.g. random squat/bench day)
- Managed via "Manage split days" main menu option (separate from session creation)
- Prompted when starting a new session, validated against DB values

---

## CLI Flow

### Login Screen
- Options: `create`, `login`, `list`
- `list` prints all registered usernames alphabetically and loops back to prompt
- `create` and `login` proceed as before
- Loops until a valid option is entered
- Duplicate username check handled in `User.register()` — exits if username exists

### Main Menu
1. Start new workout session
2. View exercise history
3. View exercise graph
4. View workouts by date
5. Manage split days
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
- Shows numbered muscle group list, user picks by number or name, or types an exercise name directly
- If muscle group entered (by number or name) → lists all exercises in that group numbered, user picks one
- If exercise name entered directly → resolves via primary name then aliases as before
- Always displays primary name in the header, even if searched by alias
- Optional intensity filter (validated against VALID_INTENSITIES)
- Shows all instances ordered by date ASC
- Format: `date | #index | intensity | sets | rest: values | notes`
- Rest omitted from output if no rest values stored for that instance

### View Exercise Graph
- Same muscle group browse flow as view history
- Calls `show_exercise_graphs(exercise_id, exercise_name, user_id)` from `graphs.py`
- Pops up a matplotlib window with 3 graphs side by side (2 for bodyweight exercises)
- Window blocks until closed, then returns to main menu

### View Workouts by Date
- If 1 session: shows full session summary directly
- If multiple sessions: lists them with session id, split day, exercise count
- User selects one, full summary shown

### Display Format
- All print functions (`_print_recent`, `prompt_view_history`, `print_session_summary`) show rest times
- Format: `sets: 225x10,225x10 | rest: 2,1.5 | notes: None`
- Rest values are comma separated, one per inter-set rest (last set has no rest)
- Rest omitted entirely if no rest values exist for that instance

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
- Contains `EXERCISE_MAPPING` dict: primary name → `{"muscle_group": "...", "aliases": [...]}`
- `VALID_MUSCLE_GROUPS` tuple exported from here: `("legs", "back", "chest", "shoulders", "biceps", "triceps")`
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
- Skips sessions that already exist (matched by user, date, split day) — safe to re-run
- Skips exercise instances that already exist in a session (matched by exercise_id, workout_index)
- Multi-set weights/reps stored as comma-separated strings e.g. `"120, 127.5"`
- Bodyweight exercises use `bw` in the CSV — converted to `0` during import
- Rest time is repeated for all sets if only one value given
- Maps all data to user `cole prochilo`
- Uses lazy session creation (same as app)
- `resolve_exercise()` checks primary name then aliases — warns if name not found in mapping
- Re-runnable safely: only new sessions and instances will be added
- Unmatched exercise names prompt interactively: shows all exercises, asks `[n] new exercise  [a] add as alias`
- `[n]`: prompts for primary name and muscle group — if primary differs from unmatched name, unmatched name is auto-saved as alias
- `[a]`: prompts for primary name to map to, saves unmatched name as alias to that primary
- Exercises added via prompt are added to DB only — update `exercise_mapping.py` manually to persist across DB resets
- `resolve_exercise()` no longer auto-creates unknown exercises

## Graphs (`graphs.py`)
- 3 graphs per exercise displayed side by side in a matplotlib popup window
- **Graph 1 — Avg Weight over Time**: all intensities as separate colored lines, y-axis is avg weight per instance. For bw exercises y-axis is avg reps, weighted instances annotated with `+Xlbs`
- **Graph 2 — e1RM by Intensity**: normal + heavy only, two colored lines. Light excluded as it's a deload intensity
- **Graph 3 — Combined e1RM**: normal + heavy combined into one line. Skipped for bw exercises
- **e1RM formula**: Epley — `weight × (1 + reps / 30)`. Calculated per set then averaged across sets per instance
- **Bodyweight detection**: majority rules — if more than half of instances have weight = 0, treated as bw exercise
- **Mixed weight/bw**: bw exercises always use reps as y-axis, weighted instances annotated with avg weight
- **X-axis**: true calendar dates with gaps (shows training frequency)
- Colors: light = skyblue, normal = steelblue, heavy = darkblue
- TODO: add download/save button to graph window

## Future Automation (TODO)
- Schedule `import_csv.py` to run automatically on a weekly basis using macOS `cron` or `launchd`
- Use `openpyxl` to read the xlsx directly so manual CSV export is not needed
- This would make the spreadsheet the source of truth and auto-sync to the DB weekly
- Manual entry at the gym still works alongside this for real-time logging

---

## Future Plans
- Data visualization ✅ — implemented in `graphs.py`
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
- No way to edit instances from past sessions (only editable during active session confirm flow) — TODO
- CSV import `MONTH_OFFSETS` needs to be updated manually as new months are added to the spreadsheet
- **ACTIVE BUG**: after closing a graph window and answering `n` to "View another graph?", the main menu re-triggers option 3 (view graph) due to a stray newline being sent to stdin when the matplotlib TkAgg window closes. Tried: termios flush, double flush with sleep, select drain. Not yet resolved.
- Fixed: `prompt_view_history` was returning `exercise_id` instead of `primary_name` when browsing by muscle group (wrong tuple index)
- Fixed: duplicate `prompt_view_history` body was left inside `prompt_view_graph` — cleaned up by extracting shared `_browse_muscle_group()` helper used by both functions

## Tab Completion
- Implemented using `gnureadline` (statically linked GNU readline, more reliable on macOS)
- Import: `try: import gnureadline as readline` with fallback to `import readline`
- `_get_exercise_completer()` loads all primary names from DB and returns a completer function
- `_input_with_exercise_completion(prompt)` sets the completer, prompts for input, then clears the completer
- Applied to exercise name prompt in `prompt_log_exercise` and `prompt_view_history`
- Completes against primary names only (not aliases) — completion is prefix-based
- Tab cycles through matches
