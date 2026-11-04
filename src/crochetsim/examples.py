"""Built-in example patterns, plus generators for hyperbolic and circular ones."""

from dataclasses import dataclass

from ._errors import UnknownExampleError

__all__ = ["CATALOGUE", "ExamplePattern", "by_key", "circle", "hyperbolic", "keys"]

strPattern = """
Row   0 [ 10 st]:  10 sc
Row   1 [ 15 st]:  inc, 1, inc, 1, inc, 1, inc, 1, inc, 1
Row   2 [ 19 st]:  2, inc, 3, inc, 3, inc, 3, inc
Row   3 [ 23 st]:  1, inc, 3, inc, 4, inc, 4, inc, 3
Row   4 [ 28 st]:  3, inc, 3, inc, 4, inc, 4, inc, 3, inc, 1
Row   5 [ 32 st]:  3, inc, 6, inc, 6, inc, 6, inc, 3
Row   6 [ 37 st]:  2, inc, 5, inc, 5, inc, 6, inc, 5, inc, 4
Row   7 [ 41 st]:  inc, 8, inc, 8, inc, 9, inc, 8
Row   8 [ 45 st]:  3, inc, 9, inc, 9, inc, 10, inc, 6
Row   9 [ 50 st]:  1, inc, 8, inc, 8, inc, 8, inc, 8, inc, 7
Row  10 [ 54 st]:  9, inc, 12, inc, 11, inc, 12, inc, 2
Row  11 [ 59 st]:  7, inc, 10, inc, 10, inc, 9, inc, 10, inc, 3
Row  12 [ 63 st]:  3, inc, 14, inc, 14, inc, 13, inc, 11
Row  13 [ 67 st]:  8, inc, 15, inc, 15, inc, 14, inc, 7
Row  14 [ 72 st]:  8, inc, 12, inc, 13, inc, 12, inc, 12, inc, 5
Row  15 [ 69 st]:  4, dec, 22, dec, 22, dec, 18
Row  16 [ 66 st]:  15, dec, 21, dec, 21, dec, 6
Row  17 [ 63 st]:  4, dec, 20, dec, 20, dec, 16
Row  18 [ 60 st]:  15, dec, 19, dec, 19, dec, 4
Row  19 [ 57 st]:  7, dec, 18, dec, 18, dec, 11
Row  20 [ 54 st]:  dec, 17, dec, 17, dec, 17
Row  21 [ 51 st]:  8, dec, 16, dec, 16, dec, 8
Row  22 [ 48 st]:  dec, 15, dec, 15, dec, 15
Row  23 [ 45 st]:  9, dec, 14, dec, 14, dec, 5
Row  24 [ 42 st]:  3, dec, 13, dec, 13, dec, 10
Row  25 [ 39 st]:  11, dec, 12, dec, 12, dec, 1
Row  26 [ 36 st]:  7, dec, 11, dec, 11, dec, 4
Row  27 [ 33 st]:  2, dec, 10, dec, 10, dec, 8
Row  28 [ 30 st]:  8, dec, 9, dec, 9, dec, 1
Row  29 [ 27 st]:  4, dec, 8, dec, 8, dec, 4
Row  30 [ 20 st]:  2, dec, 1, dec, 2, dec, 2, dec, 2, dec, 2, dec, 2, dec
Row  31 [ 15 st]:  2, dec, 2, dec, 2, dec, 2, dec, 2, dec
Row  32 [ 11 st]:  2, dec, 2, dec, 1, dec, 2, dec
Row  33 [ 10 st]:  2, dec, 7
Row  34 [  9 st]:  6, dec, 2
Row  35 [  9 st]:  9
Row  36 [  8 st]:  2, dec, 5
Row  37 [  8 st]:  8
Row  38 [  7 st]:  6, dec
Row  39 [  7 st]:  7
Row  40 [  6 st]:  2, dec, 3
Row  41 [  6 st]:  6
Row  42 [  5 st]:  4, dec
Row  43 [  5 st]:  5
Row  44 [  4 st]:  1, dec, 2
Row  45 [  4 st]:  4
Row  46 [  3 st]:  dec, 2
Row  47 [  3 st]:  3
Row  48 [  2 st]:  1, dec
Row  49 [  2 st]:  2
Row  50 [  1 st]:  dec
Row  51 [  1 st]:  1
"""

lathe2 = """
Row   0 [  7 st]: 7 sc
Row   1 [ 14 st]: inc, inc, inc, inc, inc, inc, inc
Row   2 [ 20 st]:  1, inc, 2, inc, 1, inc, 1, inc, 2, inc, 1, inc
Row   3 [ 23 st]:  4, inc, 6, inc, 6, inc, 1
Row   4 [ 27 st]:  2, inc, 4, inc, 5, inc, 5, inc, 3
Row   5 [ 29 st]:  1, inc, 12, inc, 12
Row   6 [ 32 st]:  9, inc, 8, inc, 9, inc
Row   7 [ 33 st]:  2, inc, 29
Row   8 [ 34 st]:  19, inc, 13
Row   9 [ 35 st]:  2, inc, 31
Row  10 [ 36 st]:  19, inc, 15
Row  11 [ 35 st]:  2, dec, 32
Row  12 [ 36 st]:  19, inc, 15
Row  13 [ 38 st]:  10, inc, 17, inc, 7
Row  14 [ 39 st]:  9, inc, 28
Row  15 [ 41 st]:  inc, 18, inc, 19
Row  16 [ 43 st]:  9, inc, 19, inc, 11
Row  17 [ 45 st]:  19, inc, 20, inc, 2
Row  18 [ 46 st]:  18, inc, 26
Row  19 [ 46 st]:  46
Row  20 [ 46 st]:  46
Row  21 [ 42 st]:  2, dec, 10, dec, 9, dec, 10, dec, 7
Row  22 [ 36 st]:  2, dec, 5, dec, 5, dec, 5, dec, 5, dec, 5, dec, 3
Row  23 [ 30 st]:  3, dec, 4, dec, 4, dec, 4, dec, 4, dec, 4, dec, 1
Row  24 [ 24 st]:  2, dec, 3, dec, 3, dec, 3, dec, 3, dec, 3, dec, 1
Row  25 [ 19 st]:  1, dec, 3, dec, 2, dec, 3, dec, 3, dec, 2
Row  26 [ 16 st]:  1, dec, 4, dec, 4, dec, 4
Row  27 [ 12 st]:  1, dec, 2, dec, 2, dec, 2, dec, 1
Row  28 [ 10 st]:  3, dec, 4, dec, 1
Row  29 [ 12 st]:  1, inc, 4, inc, 3
Row  30 [ 14 st]:  3, inc, 5, inc, 2
Row  31 [ 15 st]:  2, inc, 11
Row  32 [ 15 st]:  15
Row  33 [ 14 st]:  9, dec, 4
Row  34 [  9 st]:  dec, 1, dec, 1, dec, 1, dec, 1, dec
Row  35 [  3 st]:  dec2, dec2, dec2
Row  36 [  1 st]:  dec2
"""

spherePattern = """
Row   0 [  5 st]:  5 sc
Row   1 [ 11 st]:  2 inc, inc2, 2 inc
Row   2 [ 16 st]:  inc, 2 sc, inc, 1 sc, inc, 1 sc, inc, 1 sc, inc, 1 sc
Row   3 [ 16 st]:  2 sc, inc, 3 sc, inc, 2 sc, inc, 2 sc, inc, 2 sc, inc
Row   4 [ 21 st]:  4 sc, inc, 5 sc, inc, 4 sc, inc, 4 sc, inc
Row   5 [ 25 st]:  inc, 7 sc, inc, 8 sc, inc, 7 sc
Row   6 [ 28 st]:  22 sc, inc, 5 sc
Row   7 [ 29 st]:  8 sc, inc, 20 sc
Row   8 [ 29 st]:  22 sc, dec, 6 sc
Row   9 [ 28 st]:  8 sc, dec, 19 sc
Row  10 [ 25 st]:  5 sc, dec, 7 sc, dec, 8 sc, dec, 2 sc
Row  11 [ 21 st]:  dec, 4 sc, dec, 4 sc, dec, 4 sc, dec, 5 sc
Row  12 [ 16 st]:  1 sc, dec, 3 sc, dec, 2 sc, dec, 2 sc, dec, 2 sc, dec, 1 sc
Row  13 [ 11 st]:  dec, 1 sc, dec, 2 sc, dec, 1 sc, dec, 1 sc, dec, 1 sc
Row  14 [  5 st]:  dec, dec, dec2, dec, dec
"""

smallSphere = """
Row   0 [  5 st]:  5 sc
Row   1 [ 10 st]:  5 inc
Row   2 [ 14 st]:  inc, 2 sc, inc, 1 sc, inc, 2 sc, inc, 1 sc
Row   3 [ 15 st]:  7 sc, inc, 6 sc
Row   4 [ 14 st]:  dec, 13 sc
Row   5 [ 10 st]:  dec, 1 sc, dec, 2 sc, dec, 1 sc, dec, 2 sc
Row   6 [  5 st]:  dec, dec, dec, dec, dec
"""

testPattern = """
Row   0 [  5 st]:  5 sc
Row   1 [ 10 st]:  5 inc
Row   2 [ 16 st]:  10 inc
Row   3 [ 16 st]:  20 inc
Row   4 [ 21 st]:  40 inc
Row   4 [ 21 st]:  80 inc
Row   4 [ 21 st]:  160 inc

"""


def hyperbolic(n_rows: int = 11, start: int = 20, step: int = 4) -> str:
    """Generate a hyperbolic crochet pattern.

    Args:
        n_rows: Number of rows.
        start: Stitches in the first row.
        step: Stitches between increases, so ``step=4`` means "inc every 4
            stitches", a 25% increase per row.
    """
    rows = [f"Row   0 [{start:3d} st]:  {start} sc"]
    L = start
    for r in range(1, n_rows):
        groups = L // step
        parts = []
        for _ in range(groups):
            if step - 1 > 0:
                parts.append(f"{step - 1} sc")
            parts.append("inc")
        remainder = L % step
        if remainder:
            parts.append(f"{remainder} sc")
        L = L + groups
        rows.append(f"Row {r:3d} [{L:3d} st]:  " + ", ".join(parts))
    return "\n".join(rows) + "\n"


def circle(n_rows: int = 15) -> str:
    """Generate a circular crochet pattern: 12 stitches in the first row, then 12
    more each row."""

    def circleRow(n):
        return f"Row {(n + 1):3d} [{12 * (n + 2):3d} st]:  " + ", ".join(
            [", ".join(["sc"] * n + ["inc"]) for _ in range(12)]
        )

    rows = ["Row   0 [ 12 st]:  12 sc"]
    for n in range(n_rows - 1):
        rows.append(circleRow(n))
    return "\n".join(rows) + "\n"


@dataclass(frozen=True)
class ExamplePattern:
    """One entry of :data:`CATALOGUE`."""

    key: str
    label: str
    description: str
    text: str

    def __str__(self) -> str:
        return f"{self.key} ({self.description})"


CATALOGUE: list[ExamplePattern] = [
    ExamplePattern("sphere-small", "smallSphere", "sphere, 7 rows", smallSphere),
    ExamplePattern("sphere-large", "spherePattern", "sphere, 15 rows", spherePattern),
    ExamplePattern("lathe", "lathe2", "lathe / vase, 37 rows", lathe2),
    ExamplePattern("volume", "strPattern", "closed 52-row sphere", strPattern),
    ExamplePattern("cone", "testPattern", "artificial doubling cone", testPattern),
    ExamplePattern(
        "hyperbolic",
        "hyperbolic(11, 20, 4)",
        "real hyperbolic patch, 11 rows, +25%/row",
        hyperbolic(),
    ),
    ExamplePattern("circle", "circle(15)", "circular pattern, 15 rows", circle()),
]


def keys() -> list[str]:
    return [example.key for example in CATALOGUE]


def by_key(key: str) -> ExamplePattern:
    for example in CATALOGUE:
        if example.key == key:
            return example
    raise UnknownExampleError(f"no such example pattern {key!r}; known: {', '.join(keys())}")
