"""The one-call facade: pattern text in, positioned certified model out.

:func:`solve` is the whole library in one call.  Everything it returns is also
reachable through the submodules, for callers who want to drive the pieces
themselves: ``pattern`` (domain), ``examples`` (data), ``metrics`` (measurement),
``embedding`` (solver), ``display`` (presentation).
"""

from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from .embedding import EmbeddingOptimiser, EmbeddingResult, SolverConfig, UnitEdgeSolver
from .metrics import Certificate, Certifier
from .pattern import Pattern, StitchGraph

__all__ = ["Solution", "certify", "solve"]


@dataclass
class Solution:
    """A solved and certified pattern: the package's single result type.

    ``graph.positions`` is already set, so the graph is ready for
    :mod:`crochetsim.display` or further measurement.
    """

    pattern: Pattern
    graph: StitchGraph
    result: EmbeddingResult
    certificate: Certificate
    seed: int | None = None
    artifacts: list[Path] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def x(self) -> np.ndarray:
        """``(n, 3)`` coordinates indexed by node id."""
        return self.graph.positions

    @property
    def is_clean(self) -> bool:
        return self.certificate.is_clean()

    @property
    def rows(self) -> int:
        return self.pattern.row_count

    def describe(self) -> str:
        name = self.pattern.name or "pattern"
        return f"{name}: {self.result.describe()}\n{self.certificate.describe()}"

    # -- presentation ------------------------------------------------------
    # Imported inside the methods, so importing crochetsim never imports
    # matplotlib or plotly.
    def save_png(self, path, camera=None, mark_close: float = 0.0,
                 title: str = "") -> Path:
        """Write a PNG of this solution and remember it in :attr:`artifacts`."""
        from .display import Viewer

        out = Viewer().save_png(self.graph, path, camera, mark_close, title)
        self.artifacts.append(out)
        return out

    def save_html(self, path, camera=None, mark_close: float = 0.0, title: str = "",
                  open_browser: bool = False) -> Path:
        """Write the self-contained HTML model of this solution."""
        from .display import Viewer

        out = Viewer().save_html(self.graph, path, camera, mark_close, title,
                                 open_browser)
        self.artifacts.append(out)
        return out

    def show(self, camera=None, mark_close: float = 0.0, title: str = "", path=None):
        """Open the model: a browser by default, a matplotlib window as fallback."""
        from .display import Viewer

        return Viewer().show(self.graph, camera, mark_close, title, path)


def solve(pattern: str | Pattern, config: SolverConfig | None = None,
          optimiser: EmbeddingOptimiser | None = None, seed: int | None = None,
          tries: int = 5) -> Solution:
    """Validate, embed and certify a pattern.

    Parameters
    ----------
    pattern:
        Pattern text, or an already-parsed :class:`~crochetsim.pattern.Pattern`.
        Invalid patterns are refused before any solving happens.
    config, seed:
        Solver knobs.  ``seed`` overrides ``config.seed``, and is the *first* of
        the ``tries`` seeds tried.
    optimiser:
        Supply your own multi-seed strategy; it wins over ``config`` and ``seed``.
    tries:
        How many seeds to try, keeping the cleanest embedding.  Each try is a full
        solve, so ``tries=1`` is the fast, single-shot path.

    Returns
    -------
    Solution
        With positions already assigned to ``solution.graph``.
    """
    if isinstance(pattern, str):
        pattern = Pattern.from_text(pattern)
    if not isinstance(pattern, Pattern):
        raise TypeError(
            f"expected pattern text or a Pattern, got {type(pattern).__name__}"
        )
    pattern.validate().raise_if_invalid(pattern.name)

    if optimiser is None:
        solver_config = config or SolverConfig()
        if seed is not None:
            solver_config = replace(solver_config, seed=seed)
        optimiser = EmbeddingOptimiser(UnitEdgeSolver(solver_config))

    graph = pattern.to_graph()
    result, certificate = optimiser.best(graph, tries=tries)
    graph.positions = result.x
    return Solution(
        pattern=pattern,
        graph=graph,
        result=result,
        certificate=certificate,
        seed=getattr(optimiser, "last_seed", None),
        seconds=result.time,
    )


def certify(graph: StitchGraph, x=None, certifier: Certifier | None = None
            ) -> Certificate:
    """Measure an embedding that has already been solved, without re-solving it."""
    return (certifier or Certifier()).certify(graph, x)
