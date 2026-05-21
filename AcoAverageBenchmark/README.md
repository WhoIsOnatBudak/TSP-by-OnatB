# ACO Average Benchmark

This is a separate benchmark version. It keeps `AcoVariants/` untouched and
runs all algorithms over a city-count range.

`BlindBlendAS` includes the current project additions:

- linearly changing evaporation
- per-ant alpha/beta variation
- nearest-neighbor initial pheromone boost
- min-max pheromone clamp in the normal ACO update and the blind ACO update
- normal ACO pheromone deposit from only the best `pheromone_deposit_top_ants`
- blind ACO pheromone built from total edge usage counts after all blind iterations

Usage:

```sh
make run
```

Default run:

```text
100, 101, ..., 110 cities
```

Custom run:

```sh
make
./bin/aco_average 100 25
```

That runs all algorithms for:

```text
100, 101, 102, ..., 125 cities
```

Optional arguments:

```sh
./bin/aco_average <start_city> <x> <n_ants> <n_iterations> <cross_check>
```

Example:

```sh
./bin/aco_average 100 10 80 150 1
```

Outputs:

- `output/detail.csv`: one row per algorithm and city count
- `output/average.csv`: average result per algorithm
