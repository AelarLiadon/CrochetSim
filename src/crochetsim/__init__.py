"""Represent crochet patterns as graphs and embed them in 3D space.

    import crochetsim as cs

    solution = cs.solve(cs.examples.by_key("hyperbolic").text)
    solution.certificate.is_clean()
    solution.save_html("hyperbolic.html")     # needs crochetsim[view]

Importing this package never imports matplotlib or plotly: the presentation layer
is pulled in only when something is drawn, so a core install works headless.
Renderers and ``Camera`` are not re-exported here; reach them through
:mod:`crochetsim.display`.
"""

from . import examples
from ._errors import (
    CrochetError,
    InvalidPatternError,
    MissingDependencyError,
    MissingPositionsError,
    PatternSyntaxError,
    UnknownExampleError,
    UnsolvableGraphError,
)
from .api import Solution, certify, solve
from .embedding import (
    EmbeddingOptimiser,
    EmbeddingResult,
    Solver,
    SolverConfig,
    UnitEdgeSolver,
)
from .metrics import (
    Certificate,
    Certifier,
    CertifyConfig,
    FaceSet,
    SelfIntersectionDetector,
    SurfaceMetrics,
    Verdict,
)
from .pattern import (
    Pattern,
    Row,
    RowError,
    Stitch,
    StitchGraph,
    StitchKind,
    ValidationReport,
)

__version__ = "0.1.0"

__all__ = [
    "Certificate",
    "Certifier",
    "CertifyConfig",
    "CrochetError",
    "EmbeddingOptimiser",
    "EmbeddingResult",
    "FaceSet",
    "InvalidPatternError",
    "MissingDependencyError",
    "MissingPositionsError",
    "Pattern",
    "PatternSyntaxError",
    "Row",
    "RowError",
    "SelfIntersectionDetector",
    "Solution",
    "Solver",
    "SolverConfig",
    "Stitch",
    "StitchGraph",
    "StitchKind",
    "SurfaceMetrics",
    "UnitEdgeSolver",
    "UnknownExampleError",
    "UnsolvableGraphError",
    "ValidationReport",
    "Verdict",
    "certify",
    "examples",
    "solve",
]
