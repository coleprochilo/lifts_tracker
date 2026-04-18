import uuid
import sys
import bcrypt
import json

class User:
    def __init__(self, name, date_created, exs_objects=None):
        self.name = name
        self.date_created = date_created
        self.exs_objects = {} if exs_objects is None else exs_objects
        self.workouts = {}

    def register_user(self, username, password):
        with open("users.json", "r") as f:
            users = json.load(f)

        if username in users:
            sys.exit("Username already exists.")

        users[username] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        with open("users.json", "w") as f:
            json.dump(users, f)

        print(f"User {username} registered successfully.")

    def login_user(self, username, password):
        with open("users.json", "r") as f:
            users = json.load(f)

        if not username or not password:
            sys.exit("Username or password is empty.")

        if username not in users:
            sys.exit("Username not found.")

        if not bcrypt.checkpw(password.encode(), users[username].encode()):
            sys.exit("Wrong password dumb bitch.")

        print(":P You're In :p")

    def create_workout(self, date):
        workout = WorkoutSession(date)
        self.workouts[workout.workout_id] = workout
        print(f"New workout session created for {date} | id: {workout.workout_id}")
        return workout.workout_id

    def add_exercise_instance(self, new_instance, workout_id):

        name = new_instance.name.lower()

        # -------------------------
        # 1. ADD TO EXERCISE HISTORY
        # -------------------------
        found_ex = None

        for ex in self.exs_objects.values():
            if name == ex.primary_name or name in ex.other_names:
                found_ex = ex
                break

        if found_ex:
            ex = found_ex
        else:
            print(f"No exercise found for '{new_instance.name}'.")
            print("Current exercises: " + ", ".join(self.exs_objects.keys()))
            
            existing = input("Does this belong to an existing exercise? (enter primary name or leave blank to create new): ").strip().lower()
            
            if existing and existing in self.exs_objects:
                ex = self.exs_objects[existing]
                ex.other_names.append(name)
            else:
                primary = input("Enter primary name: ").strip().lower()
                other = [
                    n.strip().lower()
                    for n in input("Enter aliases (comma separated): ").split(",")
                    if n.strip()
                ]
                ex = Exercise(primary, other)
                self.exs_objects[primary] = ex

        ex.add_instance(new_instance)        # <-- here
        self._print_recent(ex, new_instance.name) 

        # -------------------------
        # 2. ADD TO WORKOUT SESSION
        # -------------------------
        workout = self.workouts.get(workout_id)

        if workout is None:
            print(f"No workout session found for id: {workout_id}")
            return
        workout.add_exercise_instance(new_instance)

    def _print_recent(self, ex, instance_name):
        print(f"\n{instance_name} added to {ex.primary_name} for {self.name}")
        print("Recent entries:")

        for inst in ex.get_recent_instances():
            print(inst)

    def get_workouts_by_date(self, date):
        matches = [w for w in self.workouts.values() if w.date == date]
        if not matches:
            print(f"No workouts found for {date}")
            return
        for w in matches:
            print(f"workout_id: {w.workout_id} | exercises: {len(w.instances)}")

class WorkoutSession:
    def __init__(self, date):
        self.workout_id = str(uuid.uuid4())
        self.date = date
        self.instances = {}

    def add_exercise_instance(self, instance):
        instance.workout_id = self.workout_id
        self.instances[instance.workout_index] = instance

    def get_ordered_instances(self):
        return [self.instances[k] for k in sorted(self.instances)]
    

class Exercise:
    def __init__(self, primary_name, other_names=None):
        self.primary_name = primary_name.lower()
        self.other_names = [n.lower() for n in (other_names or [])]
        self.exs_instances = {}

    def add_instance(self, instance):
        self.exs_instances[instance.instance_id] = instance

    def get_instances_by_date(self):
        return sorted(self.exs_instances.values(), key=lambda x: x.date)
    
    def get_recent_instances(self, n=3):
        return self.get_instances_by_date()[-n:]


class Exercise_Instance:
    def __init__(
        self,
        name,
        intensity,
        date,
        workout_index,
        notes,
        weights=None,
        reps=None,
        rest_times=None,
    ):
        self.instance_id = str(uuid.uuid4())
        self.name = name.lower()
        self.intensity = intensity
        self.date = date
        self.workout_index = workout_index
        self.notes = notes

        self.weights = weights or []
        self.reps = reps or []
        if len(self.weights) != len(self.reps):
            raise ValueError(f"weights and reps must be the same length, got {len(self.weights)} and {len(self.reps)}")
        self.sets = len(self.weights)
        self.rest_times = rest_times or []

        self.workout_id = None

    def __str__(self):
        return (
            f"{self.date} | {self.name} | sets: {self.sets} | "
            f"intensity: {self.intensity} | weights: {self.weights} | "
            f"reps: {self.reps} | workout_index: {self.workout_index} | notes: {self.notes}"
        )
    
    

if __name__ == "__main__":
    print(" -------------------- Create new user or login -------------------- \n")
    create_or_login = input("Type create to create new user, type login to login with existing user\n").lower()
    if create_or_login == "create":
        user = User.register_user(input("Username: "), input("Password: "))
    elif create_or_login == "login":
        user = User.login_user(input("Username: "), input("Password: "))
    else:
        print("I said enter create or login, what else did your dumbass type\n")
    print(" -------------------- Write down ur lifts freak -------------------- \n")
    
