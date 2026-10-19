"""Represent crochet patterns as graphs and embed them in 3D."""

from ._errors import (
    CrochetError,
    InvalidPatternError,
    MissingDependencyError,
    MissingPositionsError,
    PatternSyntaxError,
    UnknownExampleError,
    UnsolvableGraphError,
)

__version__ = "0.1.0"

__all__ = [
    "CrochetError",
    "InvalidPatternError",
    "MissingDependencyError",
    "MissingPositionsError",
    "PatternSyntaxError",
    "UnknownExampleError",
    "UnsolvableGraphError",
    "__version__",
]
