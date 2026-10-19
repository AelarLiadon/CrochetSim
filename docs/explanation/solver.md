# The solver

`UnitEdgeSolver` finds coordinates `X` such that `|X_u - X_v| = 1` on every edge.
Four things happen, in order:

1. A smooth residual `|x_u - x_v| - 1` with an **analytic sparse Jacobian** (6
   non-zeros per edge row).
2. Sparse Levenberg-Marquardt (`scipy.optimize.least_squares`, `method="trf"`).
3. Shape selection by a Laplacian bending energy, applied by continuation over
   `mus = (1e2, 1, 1e-2)`.
4. An *anchored* exactness polish.

```python
from crochetsim import Pattern, UnitEdgeSolver

graph = Pattern.from_text(text).to_graph()
graph.positions = UnitEdgeSolver().solve(graph).x
```

The solver never mutates the graph. It returns an `EmbeddingResult` holding `x`
(an `(n, 3)` array indexed by node id) plus `max_err`, `nfev`, `time`, `rgyr` and
`sphericity`. Assigning those coordinates is the caller's job, which keeps the
solver usable as a pure step in a larger pipeline.

## Why the shape prior is load-bearing

The constraint system is heavily under-determined: `m ~ 2n` constraints against
`3n - 6` degrees of freedom. LM therefore converges in ~20-40 iterations
*regardless of n* - but an unregularised solve returns an arbitrary point on an
~n-dimensional solution manifold, i.e. a crumpled tangle. The bending energy
`||mean(neighbours) - x||^2` is what chooses a sensible surface. It is not
cosmetic:

| regulariser | result |
|---|---|
| none | max edge error 57.7, 144,316 face intersections |
| `(1e2, 1, 1e-2)` | the measured sweet spot |
| `(1e6, 1e4, 1e2)` | collapses: min gap 1e-4, 10,269 near-contacts |

The polish is always *anchored* (`r = [edges; sqrt(anchor_mu) * (x - x_smooth)]`),
because a plain `mu = 0` polish random-walks along the nullspace and destroys the
shape. It costs nothing to keep: `anchor_mu` defaults to `1e-8`.

## Why this and not a spring relaxation

The earlier `springSimulationNumba` was not slow so much as *stuck*. Measured:

| method | time | max edge error |
|---|---|---|
| spring relaxation, 2,000 iterations | 4.6 s | 35 |
| spring relaxation, 26,600 iterations | 10.0 s | 36 (plateau) |
| `UnitEdgeSolver` | ~5-7 s | 2.3e-09 |

The spring method dropped to ~37 within 2 s and then oscillated between 35.5 and
37.6 forever, parked in a local minimum. Its force kernel was also quadratic - it
looped over all `n^2` node pairs testing a dense adjacency matrix, for a graph
with only `m ~ 2n` edges. Measured at n=808 (both numba): 1.925 ms/iteration for
the dense O(n^2) form versus 0.0120 ms/iteration for an O(m) edge list, a 160x
per-iteration difference, and 5.2 MB of adjacency versus 0.026 MB of edges.

Two further dead ends, both measured rather than assumed:

- A **numeric** Jacobian costs ~3n extra residual evaluations per iteration; the
  old L-BFGS-B objective used the non-smooth `abs(dist - 1)`, whose kink sits
  exactly at the solution, and stalled at `nit=8` after 3,038 evaluations.
- **Multilevel coarsening** was 6-25x *slower*, and minimum-norm Gauss-Newton 32x
  slower. There is nothing left to accelerate: the cost is one sparse solve per
  stage, and `max_nfev=60` reaches the same quality that 300 costs ~16 s to reach.

## Multiple seeds

`EmbeddingOptimiser` solves with several consecutive seeds - starting from the
solver's configured `seed` - certifies each candidate, and keeps the one with the
largest minimum non-adjacent edge gap, breaking ties on edge exactness. It records
the winning seed in `last_seed`. This is what `crochetsim.solve` uses by default;
`tries=1` is the single-shot path.
