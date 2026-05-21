# TestC++

C++17 port of the current Python TSP ACO project.

This version includes the current BlindBlend behavior:

- linearly changing evaporation
- per-ant alpha/beta variation
- nearest-neighbor initial pheromone boost
- min-max pheromone clamp
- pheromone deposit from only the best `pheromone_deposit_top_ants`
- blind ACO pheromone built from total edge usage counts after all blind rounds

Build:

```sh
make
```

Run:

```sh
make run
```

The executable prints the best path and distance. It also writes CSV and SVG
files to `output/` for cities, best tour, convergence, evaporation, and the
final pheromone matrix.
