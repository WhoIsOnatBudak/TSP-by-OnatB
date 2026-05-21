# ACO Variants Modular

This folder is a cleaned-up, modular version of `AcoVariants/`.
It keeps the same behavior and compares the same four algorithms:

- `BlindBlendAS`
- `BaselineAS`
- `ElitistAS`
- `MaxMinAS`

The code is split by responsibility:

- `types.hpp`: shared data structures and parameters
- `geometry.*`: TSP instance generation, distance calculation, and 2-opt crossing check
- `ant_builder.*`: ant path construction
- `pheromone.*`: pheromone creation, deposit, evaporation, min-max, and blending
- `blind_aco.*`: blind ACO edge-usage pheromone generation
- `aco_runner.*`: variant execution logic
- `output.*`: CSV, SVG, and terminal output
- `main.cpp`: experiment setup

Build and run:

```sh
make run
```

Outputs:

- `output/summary.csv`
- `output/convergence.csv`
- `output/convergence.svg`

