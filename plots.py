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


def plot_convergence(best_per_iteration):
    plt.figure(figsize=(8, 6))
    plt.plot(best_per_iteration, marker="o")
    plt.title("Best Distance per Iteration")
    plt.xlabel("Iteration")
    plt.ylabel("Best Distance")
    plt.grid(True)
    plt.show()


def plot_evaporation(evaporation_history):
    plt.figure(figsize=(8, 6))
    plt.plot(evaporation_history, marker="o")
    plt.title("Evaporation Rate per Iteration")
    plt.xlabel("Iteration")
    plt.ylabel("Evaporation Rate")
    plt.grid(True)
    plt.show()
