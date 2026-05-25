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

Parameter sweep:

```sh
make sweep
```

The sweep keeps the current `src/main.cpp` values as the base setup and tests
only `min_max_tau_ratio`, which controls the gap between `tau_min` and
`tau_max` in the min-max pheromone clamp. Every tested value runs with 20
different seeds. Results are written to:

- `output/parameter_sweep_detail.csv`
- `output/parameter_sweep_summary.csv`
- `output/parameter_sweep_best.txt`

For a quicker check:

```sh
./bin/parameter_sweep 2 30
```

The first argument is runs per value, and the second is city count.

Evaporation schedule sweep:

```sh
make evaporation-sweep
```

This tests linear, exponential, and logarithmic evaporation schedules with
different start/end evaporation values. Exponential and logarithmic schedules
also test several curve values to change the bend of the evaporation movement.
Results are written to:

- `output/evaporation_sweep_detail.csv`
- `output/evaporation_sweep_summary.csv`
- `output/evaporation_sweep_curves.csv`
- `output/evaporation_sweep_best.txt`

For a quicker check:

```sh
./bin/evaporation_sweep 1 20
```

The first argument is runs per case, and the second is city count.
