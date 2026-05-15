import seaborn as sns
import matplotlib

matplotlib.use('TkAgg')

import matplotlib.pyplot as plt


def plot_cities(coords):
    plt.figure(figsize=(8, 6))
    plt.scatter(coords[:, 0], coords[:, 1], s=100)

    for i, (x, y) in enumerate(coords):
        plt.text(x + 1, y + 1, str(i), fontsize=10)

    plt.title("Generated Cities")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(True)
    plt.show()


def plot_best_tour(coords, best_path):
    plt.figure(figsize=(8, 6))

    for i, (x, y) in enumerate(coords):
        plt.scatter(x, y, s=100)
        plt.text(x + 1, y + 1, str(i), fontsize=10)

    for i in range(len(best_path) - 1):
        a = best_path[i]
        b = best_path[i + 1]
        x_values = [coords[a][0], coords[b][0]]
        y_values = [coords[a][1], coords[b][1]]
        plt.plot(x_values, y_values)

    a = best_path[-1]
    b = best_path[0]
    x_values = [coords[a][0], coords[b][0]]
    y_values = [coords[a][1], coords[b][1]]
    plt.plot(x_values, y_values)

    plt.title("Best Tour Found by ACO")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(True)
    plt.show()


def plot_pheromone_heatmap(pheromone):
    plt.figure(figsize=(8, 6))
    sns.heatmap(pheromone, annot=True, fmt=".2f", cmap="viridis")
    plt.title("Final Pheromone Matrix")
    plt.xlabel("City")
    plt.ylabel("City")
    plt.show()


def plot_convergence(best_per_iteration, blind_round_history=None):
    plt.figure(figsize=(8, 6))
    grouped_blind_rounds = {}

    if blind_round_history:
        for blind_round in blind_round_history:
            grouped_blind_rounds.setdefault(
                blind_round["aco_iteration"],
                []
            ).append(blind_round)

    events = []

    for iteration, best_distance in enumerate(best_per_iteration):
        events.append({
            "type": "aco",
            "iteration": iteration,
            "best_distance": best_distance
        })

        blind_rounds = sorted(
            grouped_blind_rounds.get(iteration, []),
            key=lambda blind_round: blind_round["blind_iteration"]
        )

        for blind_round in blind_rounds:
            events.append({
                "type": "blind",
                "iteration": iteration,
                "blind_iteration": blind_round["blind_iteration"],
                "best_distance": blind_round["best_distance"]
            })

    for event_index in range(1, len(events)):
        previous_event = events[event_index - 1]
        current_event = events[event_index]
        is_blind_segment = current_event["type"] == "blind"

        plt.plot(
            [event_index, event_index + 1],
            [
                previous_event["best_distance"],
                current_event["best_distance"]
            ],
            color="tab:orange" if is_blind_segment else "tab:blue",
            linestyle="--" if is_blind_segment else "-",
            linewidth=2,
            alpha=0.9
        )

    aco_x_values = [
        event_index
        for event_index, event in enumerate(events, start=1)
        if event["type"] == "aco"
    ]
    aco_y_values = [
        event["best_distance"]
        for event in events
        if event["type"] == "aco"
    ]
    blind_x_values = [
        event_index
        for event_index, event in enumerate(events, start=1)
        if event["type"] == "blind"
    ]
    blind_y_values = [
        event["best_distance"]
        for event in events
        if event["type"] == "blind"
    ]

    plt.scatter(
        aco_x_values,
        aco_y_values,
        marker="o",
        color="tab:blue",
        label="ACO Iterations",
        zorder=3
    )

    if blind_x_values:
        plt.scatter(
            blind_x_values,
            blind_y_values,
            marker="s",
            color="tab:orange",
            edgecolors="tab:red",
            label="Blind ACO Rounds",
            zorder=4
        )

    aco_tick_labels = [
        event["iteration"] + 1
        for event in events
        if event["type"] == "aco"
    ]

    if len(aco_x_values) <= 40:
        plt.xticks(
            aco_x_values,
            aco_tick_labels,
            rotation=45 if len(aco_x_values) > 20 else 0
        )

    plt.title("Best Distance per Iteration")
    plt.xlabel("ACO Iteration (Blind Rounds Inserted)")
    plt.ylabel("Best Distance")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_evaporation(evaporation_history):
    plt.figure(figsize=(8, 6))
    plt.plot(evaporation_history, marker="o")
    plt.title("Evaporation Rate per Iteration")
    plt.xlabel("Iteration")
    plt.ylabel("Evaporation Rate")
    plt.grid(True)
    plt.show()
