"""Calibrated one-solve results, and the helper that reproduces them.

Every number here comes from a single ``UnitEdgeSolver(SolverConfig(seed=3))``
solve - no multi-seed search - so it is reproducible and independent of
``EmbeddingOptimiser``.  These match ``REFACTOR.md`` section 9 exactly.

``max_err`` is an optimiser artefact: it moves with the scipy/BLAS version, so it
is asserted as a *ceiling* an order of magnitude above the calibrated value.  That
still catches any real regression, because a broken solve lands at 1e-1 or worse,
never at 1e-6.  ``min_nonadjacent`` is asserted loosely for the same reason.
``n``, ``m``, ``faces``, ``crossings`` and the verdict are discrete, so they are
asserted exactly.
"""

from dataclasses import dataclass

from crochetsim.embedding import SolverConfig, UnitEdgeSolver
from crochetsim.examples import by_key
from crochetsim.metrics import Certificate, Certifier
from crochetsim.pattern import Pattern, StitchGraph

SEED = 3


@dataclass(frozen=True)
class Golden:
    """One calibrated row: what a single seed-3 solve produces for a pattern."""

    key: str
    n: int
    m: int
    max_err: float  # calibrated value, recorded for reference
    max_err_ceiling: float  # asserted: comfortably above, still decisive
    min_gap: float
    crossings: int
    verdict: str
    faces: int


GOLDEN: tuple[Golden, ...] = (
    Golden("sphere-small", 73, 151, 9.193e-11, 1e-6, 0.8660, 0, "clean", 80),
    Golden("sphere-large", 300, 620, 4.375e-09, 1e-6, 0.8630, 0, "clean", 322),
    Golden("lathe", 977, 1997, 9.771e-08, 1e-6, 0.7071, 0, "tight", 1022),
    Golden("volume", 1481, 3019, 8.094e-07, 1e-5, 0.0029, 84, "defective", 1540),
    Golden("cone", 635, 1265, 6.357e-08, 1e-6, 0.0013, 128, "defective", 632),
    Golden("hyperbolic", 808, 1596, 2.331e-09, 1e-6, 0.8359, 0, "clean", 790),
)


def pattern_for(golden: Golden) -> Pattern:
    """The catalogue pattern a golden row refers to."""
    return Pattern.from_text(by_key(golden.key).text, name=golden.key)


def solve(golden: Golden) -> tuple[StitchGraph, Certificate]:
    """Solve once at :data:`SEED` and certify it, as ``REFACTOR.md`` did."""
    graph = pattern_for(golden).to_graph()
    result = UnitEdgeSolver(SolverConfig(seed=SEED)).solve(graph)
    return graph, Certifier().certify(graph, result.x)
