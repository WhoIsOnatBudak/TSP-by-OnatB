import numpy as np
import random
import seaborn as sns
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

random.seed(57)
np.random.seed(57)


def generate_euclidean_distances(n_cities, seed=42, scale=100):
    np.random.seed(seed)
    coords = np.random.rand(n_cities, 2) * scale
    distances = np.zeros((n_cities, n_cities), dtype=float)

    for i in range(n_cities):
        for j in range(n_cities):
            distances[i][j] = np.linalg.norm(coords[i] - coords[j])

    return distances, coords


def calculate_distance(path, distances):
    total = 0
    for i in range(len(path) - 1):
        total += distances[path[i]][path[i + 1]]
    total += distances[path[-1]][path[0]]
    return total


#def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # sabit
#    return 0.5

def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation):  # Lineer azalma / best
    progress = iteration / (n_iterations - 1)
    evaporation = start_evaporation - (start_evaporation - end_evaporation) * progress
    return evaporation

#def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # Üssel azalma
#    progress = np.log1p(iteration) / np.log1p(n_iterations - 1)
#    evaporation = start_evaporation - (start_evaporation - end_evaporation) * progress
#    return evaporation

#def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # Logaritmik azalma
#    ratio = iteration / (n_iterations - 1)
#    evaporation = start_evaporation * ((end_evaporation / start_evaporation) ** ratio)
#    return evaporation


def run_aco(
    distances,
    n_ants=20,
    n_iterations=100,
    alpha=1,
    beta=3,
    evaporation=0.5,
    q=100,
    end_evaporation=0.1
):
    n_cities = len(distances)
    pheromone = np.ones((n_cities, n_cities), dtype=float)

    global_best_distance = float("inf")
    global_best_path = None
    best_per_iteration = []
    evaporation_history = []

    for iteration in range(n_iterations):
        all_paths = []
        all_distances = []

        current_evaporation = get_evaporation_rate(
            iteration=iteration,
            n_iterations=n_iterations,
            start_evaporation=evaporation,
            end_evaporation=end_evaporation
        )
        evaporation_history.append(current_evaporation)

        for ant in range(n_ants):
            start_city = random.randint(0, n_cities - 1)
            visited = [start_city]
            visited_set = {start_city}

            while len(visited) < n_cities:
                current = visited[-1]
                probabilities = np.zeros(n_cities, dtype=float)

                for city in range(n_cities):
                    if city not in visited_set:
                        tau = pheromone[current][city] ** alpha
                        eta = (1.0 / distances[current][city]) ** beta
                        probabilities[city] = tau * eta

                total_probability = probabilities.sum()

                if total_probability == 0:
                    candidates = [city for city in range(n_cities) if city not in visited_set]
                    next_city = random.choice(candidates)
                else:
                    probabilities /= total_probability
                    next_city = np.random.choice(np.arange(n_cities), p=probabilities)

                visited.append(next_city)
                visited_set.add(next_city)

            dist = calculate_distance(visited, distances)
            all_paths.append(visited)
            all_distances.append(dist)

            if dist < global_best_distance:
                global_best_distance = dist
                global_best_path = visited[:]

        best_per_iteration.append(min(all_distances))

        pheromone *= (1 - current_evaporation)

        for path, dist in zip(all_paths, all_distances):
            deposit = q / dist

            for i in range(len(path) - 1):
                a = path[i]
                b = path[i + 1]
                pheromone[a][b] += deposit
                pheromone[b][a] += deposit

            a = path[-1]
            b = path[0]
            pheromone[a][b] += deposit
            pheromone[b][a] += deposit

    return global_best_path, global_best_distance, pheromone, best_per_iteration, evaporation_history


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


n_cities = 100
distances, coords = generate_euclidean_distances(n_cities=n_cities, seed=42, scale=n_cities * 20)

best_path, best_distance, pheromone, best_per_iteration, evaporation_history = run_aco(
    distances=distances,
    n_ants=30,
    n_iterations=200,
    alpha=1,
    beta=3,
    evaporation=0.8,
    q=100,
    end_evaporation=0.3
)

print("Best Path:", best_path)
print("Best Distance:", best_distance)

plot_cities(coords)
plot_best_tour(coords, best_path)
#plot_pheromone_heatmap(pheromone)
plot_convergence(best_per_iteration)
plot_evaporation(evaporation_history)