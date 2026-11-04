"""Solve for a unit-edge embedding of a stitch graph.

Find coordinates ``X in R^(3n)`` with ``|X_u - X_v| = 1`` for every edge.  Sparse
Levenberg-Marquardt minimises the smooth residual ``|X_u - X_v| - 1``; a
row-normalised Laplacian bending energy applied by continuation selects a shape,
and an anchored polish then tightens the edges without moving that shape.  The
design and its calibration are written up in ``docs/explanation/solver.md``.

The solvers do not mutate the graph: assign ``graph.positions = result.x``
yourself.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.optimize import least_squares

from .metrics import Certificate, Certifier, edge_lengths
from .pattern import StitchGraph

__all__ = [
    "DEFAULT_ANCHOR_MU",
    "DEFAULT_MAX_NFEV",
    "DEFAULT_MUS",
    "DEFAULT_SEED",
    "EmbeddingOptimiser",
    "EmbeddingResult",
    "Solver",
    "SolverConfig",
    "UnitEdgeSolver",
]

# Solver defaults.
DEFAULT_MUS = (1e2, 1.0, 1e-2)
DEFAULT_ANCHOR_MU = 1e-8
DEFAULT_SEED = 3
DEFAULT_MAX_NFEV = 60


@dataclass
class SolverConfig:
    """Solver knobs for :class:`UnitEdgeSolver`.

    Args:
        mus: Bending-energy weights applied in order by continuation.  Empty for a
            pure constraint solve: fast and exact, but the shape is an arbitrary
            point of the solution manifold.
        anchor_mu: Weight of the anchored polish.
        seed: Initialisation seed.  Different seeds give different valid solutions.
        max_nfev: Per-stage iteration cap, and the main speed knob.
        polish: ``"anchored"`` tightens the edge residual while staying near the
            regularised solution.  ``"free"`` is an unanchored polish.  ``None``
            stops after the last ``mu``, leaving edges exact only to ~sqrt(mu).
    """

    mus: tuple = DEFAULT_MUS
    anchor_mu: float = DEFAULT_ANCHOR_MU
    seed: int = DEFAULT_SEED
    max_nfev: int = DEFAULT_MAX_NFEV
    polish: str | None = "anchored"


@dataclass
class EmbeddingResult:
    """Where :class:`UnitEdgeSolver` placed the nodes, and how well it did.

    ``x`` is an ``(n, 3)`` array indexed by node id, the same convention as
    ``StitchGraph.positions``.
    """

    x: np.ndarray
    max_err: float
    sum_err: float
    nfev: int
    time: float
    rgyr: float
    sphericity: float

    def is_exact(self, tol: float = 1e-6) -> bool:
        """True when the worst edge is within ``tol`` of unit length."""
        return self.max_err < tol

    def describe(self) -> str:
        return (
            f"n={len(self.x)}  {self.nfev} nfev  {self.time:.1f}s  "
            f"max|len-1|={self.max_err:.2e}  rgyr={self.rgyr:.2f}"
        )


def _make_edge_functions(e, n):
    """Return ``(residual, jacobian, m)`` for ``r_e = |x_u - x_v| - 1``.

    The Jacobian is sparse, with exactly 6 non-zeros per row, so it costs O(m) to
    assemble.
    """
    e = np.asarray(e, dtype=np.int64).reshape(-1, 2)
    m = len(e)
    src, dst = e[:, 0], e[:, 1]
    cols_u = (src[:, None] * 3 + np.arange(3)).ravel()
    cols_v = (dst[:, None] * 3 + np.arange(3)).ravel()
    rows = np.repeat(np.arange(m), 3)
    jrows = np.concatenate([rows, rows])
    jcols = np.concatenate([cols_u, cols_v])

    def residual(x):
        X = np.asarray(x, dtype=float).reshape(n, 3)
        d = np.linalg.norm(X[src] - X[dst], axis=1)
        return d - 1.0

    def jacobian(x):
        X = np.asarray(x, dtype=float).reshape(n, 3)
        diff = X[src] - X[dst]
        d = np.linalg.norm(diff, axis=1)
        u = diff / np.maximum(d, 1e-12)[:, None]  # d(|x_u-x_v|)/d(x_u)
        data = np.concatenate([u.ravel(), -u.ravel()])
        return sp.coo_matrix((data, (jrows, jcols)), shape=(m, 3 * n)).tocsr()

    return residual, jacobian, m


def _bending_operator(graph: StitchGraph) -> sp.csr_matrix:
    """Row-normalised graph Laplacian ``M = D^-1 A - I``.

    ``||M x||^2`` is the bending energy, i.e. the sum of squared deviations of
    each node from the mean of its neighbours.
    """
    n = graph.n
    A = nx.to_scipy_sparse_array(graph.graph, nodelist=range(n), format="csr").astype(float)
    deg = np.asarray(A.sum(1)).ravel()
    deg[deg == 0] = 1.0
    return (sp.diags(1.0 / deg) @ A - sp.identity(n, format="csr")).tocsr()


def _rgyr(x) -> float:
    X = np.asarray(x, dtype=float).reshape(-1, 3)
    return float(np.sqrt(((X - X.mean(0)) ** 2).sum(1).mean()))


def _sphericity(x) -> float:
    X = np.asarray(x, dtype=float).reshape(-1, 3)
    r = np.linalg.norm(X - X.mean(0), axis=1)
    return float(r.std() / r.mean())


class Solver(ABC):
    """Anything that can place the nodes of a :class:`StitchGraph`."""

    @abstractmethod
    def solve(self, graph: StitchGraph, x0=None) -> EmbeddingResult:
        """Return coordinates for ``graph``.  Must not mutate ``graph``."""


class UnitEdgeSolver(Solver):
    """Embed so that every edge has length 1, to ~1e-9."""

    def __init__(self, config: SolverConfig | None = None):
        self.config = config or SolverConfig()

    def solve(self, graph: StitchGraph, x0=None) -> EmbeddingResult:
        cfg = self.config
        n = graph.n
        e = graph.edge_array()
        residual, jacobian, _ = _make_edge_functions(e, n)
        M3 = sp.kron(_bending_operator(graph), sp.identity(3, format="csr"), format="csr")

        if x0 is None:
            rng = np.random.default_rng(cfg.seed)
            x = rng.normal(size=3 * n) * n ** (1 / 3)
        else:
            x = np.asarray(x0, dtype=float).reshape(-1).copy()

        t0 = time.perf_counter()
        nfev = 0

        def stage(fun, jac):
            nonlocal x, nfev
            res = least_squares(
                fun,
                x,
                jac=jac,
                method="trf",
                x_scale="jac",
                ftol=1e-14,
                xtol=1e-14,
                gtol=1e-14,
                max_nfev=cfg.max_nfev,
            )
            x = res.x
            nfev += res.nfev

        for mu in cfg.mus:
            s = np.sqrt(mu)
            stage(
                lambda xx, s=s: np.concatenate([residual(xx), s * (M3 @ xx)]),
                lambda xx, s=s: sp.vstack([jacobian(xx), s * M3]).tocsr(),
            )

        x_smooth = x.copy()
        if cfg.polish == "free":
            stage(residual, jacobian)
        elif cfg.polish == "anchored":
            s = np.sqrt(cfg.anchor_mu)
            stage(
                lambda xx, s=s: np.concatenate([residual(xx), s * (xx - x_smooth)]),
                lambda xx, s=s: sp.vstack(
                    [jacobian(xx), s * sp.identity(3 * n, format="csr")]
                ).tocsr(),
            )
        elif cfg.polish is not None:
            raise ValueError(f"unknown polish mode: {cfg.polish!r}")

        d = edge_lengths(x, e)
        X = x.reshape(n, 3)
        return EmbeddingResult(
            x=X,
            max_err=float(np.abs(d - 1).max()),
            sum_err=float(np.abs(d - 1).sum()),
            nfev=nfev,
            time=time.perf_counter() - t0,
            rgyr=_rgyr(X),
            sphericity=_sphericity(X),
        )


class EmbeddingOptimiser:
    """Solve with several seeds and keep the cleanest embedding.

    Each candidate is certified and ranked by the largest minimum non-adjacent
    edge gap, breaking ties on edge exactness.  Does not write to the graph.
    """

    def __init__(self, solver: Solver | None = None, certifier: Certifier | None = None):
        self.solver = solver or UnitEdgeSolver()
        self.certifier = certifier or Certifier()
        self.last_seed: int | None = None

    def _solver_for(self, seed: int) -> Solver:
        if isinstance(self.solver, UnitEdgeSolver):
            return UnitEdgeSolver(replace(self.solver.config, seed=seed))
        return self.solver

    def _default_seeds(self, tries: int) -> list[int]:
        """``tries`` consecutive seeds, starting from the solver's own seed."""
        base = self.solver.config.seed if isinstance(self.solver, UnitEdgeSolver) else 0
        return [base + i for i in range(tries)]

    @staticmethod
    def _rank(result: EmbeddingResult, cert: Certificate) -> tuple:
        return (cert.is_clean(), cert.min_nonadjacent, -result.max_err)

    def best(
        self, graph: StitchGraph, tries: int = 5, seeds=None
    ) -> tuple[EmbeddingResult, Certificate]:
        seeds = list(seeds) if seeds is not None else self._default_seeds(tries)
        best = None
        for seed in seeds:
            result = self._solver_for(seed).solve(graph)
            cert = self.certifier.certify(graph, result.x)
            key = self._rank(result, cert)
            if best is None or key > best[0]:
                best = (key, result, cert, seed)
        _, result, cert, seed = best
        self.last_seed = seed
        return result, cert
