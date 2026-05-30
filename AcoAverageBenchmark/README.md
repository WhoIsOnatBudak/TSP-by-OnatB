# ACO Average Benchmark

This is a separate benchmark version. It keeps `AcoVariants/` untouched and
runs all algorithms over the fixed benchmark sizes `100`, `150`, `200`, and
`250`.

For the comparison algorithm, `MaxMinAS` uses the paper-style MMAS pheromone
limits with `p_best = 0.05`:

```text
p_dec = p_best^(1 / n_cities)
tau_min = tau_max * (1 - p_dec) / ((n_cities / 2 - 1) * p_dec)
```

`BlindBlendAS` keeps the current project-specific min-max clamp so the custom
algorithm remains fixed during the benchmark.

`BlindBlendAS` includes the current project additions:

- configurable evaporation schedule; current benchmark default is exponential
  `0.6 -> 0.2` with curve `-2.0`
- per-ant alpha/beta variation
- nearest-neighbor initial pheromone boost
- min-max pheromone clamp in the normal ACO update and the blind ACO update
- normal ACO pheromone deposit from only the best `pheromone_deposit_top_ants`
- blind ACO pheromone built from total edge usage counts after all blind iterations

Current `BlindBlendAS` defaults are aligned with `TestC++/src/main.cpp`:

- `n_ants = 100`
- `n_iterations = 200`
- `nearest_neighbor_pheromone = 2.0`
- `blind_stagnation_limit = 30`
- `blind_iterations = 5`
- `blind_blend_weight = 0.5`
- `ant_parameter_variation = 0.1`
- `pheromone_deposit_top_ants = 1`

Usage:

```sh
make run
```

Default run:

```text
101 runs for each of 100, 150, 200, and 250 cities, without cross-check
```

Custom run:

```sh
make
./bin/aco_average 100 25
```

That runs all algorithms for 26 generated maps per city size, with run ids:

```text
100, 101, 102, ..., 125
```

Optional arguments:

```sh
./bin/aco_average <start_run_id> <run_span> <n_ants> <n_iterations> <cross_check>
```

Example:

```sh
./bin/aco_average 100 100 80 150 1
```

Map generation still uses the existing seed logic:

```text
map seed = 47 + run_id
algorithm seed = 43 + n_cities
```

The run id range is inclusive, matching the old benchmark behavior:

```text
start_run_id..start_run_id+run_span
```

Outputs:

- `output/detail_nc_all100.csv`, `output/average_nc_all100.csv`,
  `output/iterations_nc_all100.csv` when `cross_check = 0`
- same pattern for `150`, `200`, and `250`
- when `cross_check = 1`, the selected output set uses `wc` instead of `nc`
