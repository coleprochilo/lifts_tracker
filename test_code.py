    user = User("cole", "2025-02-21")

    workout_id = user.create_workout("2025-04-16")

    inst1 = Exercise_Instance("squat", "heavy", "2025-4-16", 1, "felt good", weights=[135, 145], reps=[8,8])
    inst2 = Exercise_Instance("bench press", "light", "2025-04-16", 2, "tough", weights=[135, 145], reps=[8,8])

    user.add_exercise_instance(inst1, workout_id)
    user.add_exercise_instance(inst2, workout_id)

    user.get_workouts_by_date("2025-04-16")