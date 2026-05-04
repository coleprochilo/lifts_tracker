import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from db import get_conn


def _e1rm(weight, reps):
    return weight * (1 + reps / 30)


def _fetch_instances(exercise_id, user_id):
    """
    Returns all instances for an exercise as a list of dicts:
    {date, intensity, sets: [{weight, reps}]}
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT ws.date, ei.intensity, es.weight, es.reps
            FROM exercise_instances ei
            JOIN workout_sessions ws ON ws.workout_id = ei.workout_id
            JOIN exercise_sets es ON es.instance_id = ei.instance_id
            WHERE ei.exercise_id = ? AND ws.user_id = ?
            ORDER BY ws.date ASC, ei.instance_id ASC, es.set_number ASC
        """, (exercise_id, user_id)).fetchall()

    instances = {}
    for date, intensity, weight, reps in rows:
        key = (date, intensity)
        instances.setdefault(key, []).append({"weight": weight, "reps": reps})

    return [
        {"date": datetime.strptime(k[0], "%Y-%m-%d"), "intensity": k[1], "sets": v}
        for k, v in instances.items()
    ]


def _is_bw_exercise(instances):
    bw_count = sum(1 for inst in instances if all(s["weight"] == 0 for s in inst["sets"]))
    return bw_count > len(instances) / 2


def _avg_weight(sets):
    return sum(s["weight"] for s in sets) / len(sets)


def _avg_reps(sets):
    return sum(s["reps"] for s in sets) / len(sets)


def _avg_e1rm(sets):
    return sum(_e1rm(s["weight"], s["reps"]) for s in sets) / len(sets)


INTENSITY_COLORS = {"light": "skyblue", "normal": "steelblue", "heavy": "darkblue"}


def _plot_graph1(ax, instances, is_bw, exercise_name):
    """Average weight (or reps for bw) over time, all intensities."""
    ax.set_title(f"{exercise_name} — Avg {'Reps' if is_bw else 'Weight'} over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Avg Reps" if is_bw else "Avg Weight (lbs)")

    by_intensity = {}
    for inst in instances:
        by_intensity.setdefault(inst["intensity"], []).append(inst)

    for intensity, insts in by_intensity.items():
        dates = [i["date"] for i in insts]
        if is_bw:
            values = [_avg_reps(i["sets"]) for i in insts]
            annotations = [
                f'+{_avg_weight(i["sets"]):.1f}lbs'
                if any(s["weight"] > 0 for s in i["sets"]) else None
                for i in insts
            ]
        else:
            values = [_avg_weight(i["sets"]) for i in insts]
            annotations = [None] * len(insts)

        color = INTENSITY_COLORS.get(intensity, "gray")
        ax.plot(dates, values, marker="o", label=intensity, color=color)

        for x, y, note in zip(dates, values, annotations):
            if note:
                ax.annotate(note, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=7)

    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())


def _plot_graph2(ax, instances, exercise_name):
    """e1RM by intensity (normal + heavy only) over time."""
    ax.set_title(f"{exercise_name} — e1RM by Intensity (normal + heavy)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Estimated 1RM (lbs)")

    by_intensity = {}
    for inst in instances:
        if inst["intensity"] in ("normal", "heavy"):
            by_intensity.setdefault(inst["intensity"], []).append(inst)

    for intensity, insts in by_intensity.items():
        dates = [i["date"] for i in insts]
        values = [_avg_e1rm(i["sets"]) for i in insts]
        color = INTENSITY_COLORS.get(intensity, "gray")
        ax.plot(dates, values, marker="o", label=intensity, color=color)

    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())


def _plot_graph3(ax, instances, exercise_name):
    """Combined e1RM (normal + heavy) over time."""
    ax.set_title(f"{exercise_name} — Combined e1RM (normal + heavy)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Estimated 1RM (lbs)")

    insts = [i for i in instances if i["intensity"] in ("normal", "heavy")]
    insts.sort(key=lambda i: i["date"])

    dates = [i["date"] for i in insts]
    values = [_avg_e1rm(i["sets"]) for i in insts]

    ax.plot(dates, values, marker="o", color="darkblue")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())


def show_exercise_graphs(exercise_id, exercise_name, user_id):
    instances = _fetch_instances(exercise_id, user_id)

    if not instances:
        print(f"No data found for '{exercise_name}'.")
        return

    # check if there is any data for normal/heavy before building graphs 2 and 3
    has_weighted_intensity = any(i["intensity"] in ("normal", "heavy") for i in instances)

    is_bw = _is_bw_exercise(instances)
    num_graphs = 2 if is_bw else 3
    if not has_weighted_intensity:
        num_graphs = 1
    fig, axes = plt.subplots(1, num_graphs, figsize=(6 * num_graphs, 5))
    axes = [axes] if num_graphs == 1 else list(axes)

    fig.suptitle(exercise_name.title(), fontsize=14, fontweight="bold")

    _plot_graph1(axes[0], instances, is_bw, exercise_name)
    if num_graphs >= 2:
        _plot_graph2(axes[1], instances, exercise_name)
    if num_graphs == 3:
        _plot_graph3(axes[2], instances, exercise_name)

    plt.tight_layout()
    plt.show()
