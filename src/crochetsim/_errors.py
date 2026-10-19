"""Exceptions raised by :mod:`crochetsim`.

One hierarchy, so ``except CrochetError`` catches everything this package raises
deliberately.  Each class also inherits from the builtin it used to be raised as
(``ValueError``, ``KeyError``, ``ImportError``), so code written against the flat
modules - ``except ValueError:`` - keeps working.
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
    """Base class for every error this package raises deliberately."""


class PatternSyntaxError(CrochetError, ValueError):
    """A stitch token or row line could not be parsed."""


class InvalidPatternError(CrochetError, ValueError):
    """A parsed pattern does not work into its own rows.

    Raised by :meth:`crochetsim.pattern.ValidationReport.raise_if_invalid`;
    :meth:`crochetsim.pattern.Pattern.validate` reports instead of raising.
    """


class UnsolvableGraphError(CrochetError, ValueError):
    """The graph cannot be embedded as given: bad node labels, or empty."""


class MissingPositionsError(CrochetError, ValueError):
    """Coordinates are required but the graph has none: solve it first."""


class MissingDependencyError(CrochetError, ImportError):
    """An optional view dependency is needed: install ``crochetsim[view]``."""


class UnknownExampleError(CrochetError, KeyError):
    """No catalogue entry with that key."""
