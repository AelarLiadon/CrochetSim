"""Exceptions raised by :mod:`crochetsim`.

Every deliberate error derives from :class:`CrochetError`.  Each class also
inherits the closest builtin (``ValueError``, ``KeyError``, ``ImportError``), so
ordinary ``except`` clauses keep working.
"""

__all__ = [
    "CrochetError",
    "InvalidPatternError",
    "MissingDependencyError",
    "MissingPositionsError",
    "PatternSyntaxError",
    "UnknownExampleError",
    "UnsolvableGraphError",
]


class CrochetError(Exception):
    """Base class for every error raised by this package."""


class PatternSyntaxError(CrochetError, ValueError):
    """A stitch token or row line could not be parsed."""


class InvalidPatternError(CrochetError, ValueError):
    """A parsed pattern does not work into its own rows.

    Raised by :meth:`crochetsim.pattern.ValidationReport.raise_if_invalid`;
    :meth:`crochetsim.pattern.Pattern.validate` reports instead of raising.
    """


class UnsolvableGraphError(CrochetError, ValueError):
    """The graph cannot be embedded as given, e.g. its node labels are not ``0..n-1``."""


class MissingPositionsError(CrochetError, ValueError):
    """Coordinates are required but the graph has none: solve it first."""


class MissingDependencyError(CrochetError, ImportError):
    """An optional view dependency is needed: install ``crochetsim[view]``."""


class UnknownExampleError(CrochetError, KeyError):
    """No catalogue entry with that key."""
