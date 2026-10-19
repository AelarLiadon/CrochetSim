import random
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum

import networkx as nx
import numpy as np

from ._errors import InvalidPatternError, PatternSyntaxError, UnsolvableGraphError

__all__ = [
    "Pattern",
    "Row",
    "RowError",
    "Stitch",
    "StitchGraph",
    "StitchKind",
    "ValidationReport",
]


class StitchKind(Enum):
    """The three stitch types, with their production and consumption counts."""

    SC = "sc"
    INC = "inc"
    DEC = "dec"

    def produces(self, repeat: int = 1) -> int:
        """Stitches created in the new row.  ``inc`` -> 2, ``incN`` -> N+1."""
        if self is StitchKind.SC:
            return 1
        if self is StitchKind.DEC:
            return 1
        return repeat + 1

    def consumes(self, repeat: int = 1) -> int:
        """Stitches of the row below worked into.  ``dec`` -> 2, ``decN`` -> N+1."""
        if self is StitchKind.SC:
            return 1
        if self is StitchKind.INC:
            return 1
        return repeat + 1

    @classmethod
    def parse(cls, token: str) -> tuple["StitchKind", int]:
        """Split a stitch token into (kind, repeat).  ``"inc2"`` -> (INC, 2)."""
        for kind in cls:
            if token.startswith(kind.value):
                rest = token[len(kind.value) :]
                if rest == "":
                    return kind, 1
                if rest.isdigit():
                    return kind, int(rest)
        raise PatternSyntaxError(f"unknown stitch token {token!r}")

    @classmethod
    def try_parse(cls, token: str):
        """Like :meth:`parse` but returns ``(None, None)`` instead of raising."""
        try:
            return cls.parse(token)
        except ValueError:
            return None, None


@dataclass(frozen=True)
class Stitch:
    """One stitch instruction, e.g. ``sc``, ``inc``, ``dec2``."""

    kind: StitchKind
    repeat: int = 1

    def produces(self) -> int:
        return self.kind.produces(self.repeat)

    def consumes(self) -> int:
        return self.kind.consumes(self.repeat)

    def to_token(self) -> str:
        return self.kind.value if self.repeat == 1 else f"{self.kind.value}{self.repeat}"

    @classmethod
    def parse(cls, token: str) -> "Stitch":
        kind, repeat = StitchKind.parse(token)
        return cls(kind, repeat)

    @classmethod
    def parse_many(cls, token: str) -> list["Stitch"]:
        """Expand one text token into stitches.

        ``"2 inc"`` is two separate increases; ``"inc2"`` is one increase of size 2.
        """
        token = token.strip()
        if not token:
            return []
        if token.isnumeric():
            return [cls(StitchKind.SC)] * int(token)
        if " " in token:
            left, _, right = token.partition(" ")
            left, right = left.strip(), right.strip()
            if left.isnumeric():
                return [cls.parse(right)] * int(left)
            raise PatternSyntaxError(f"invalid stitch representation: {token!r}")
        return [cls.parse(token)]


@dataclass(frozen=True)
class Row:
    """One row of a pattern: an ordered sequence of stitches."""

    index: int
    stitches: tuple[Stitch, ...] = ()

    def __post_init__(self) -> None:
        # Accept any sequence, store a tuple.  Frozen and hashable, so it cannot
        # change under a StitchGraph that has cached a reference to it.
        object.__setattr__(self, "stitches", tuple(self.stitches))

    @property
    def stitch_count(self) -> int:
        """Stitches this row *produces*."""
        return sum(st.produces() for st in self.stitches)

    @property
    def parent_slots(self) -> int:
        """Stitches of the row below this row works into."""
        return sum(st.consumes() for st in self.stitches)

    def pack(self) -> str:
        """Run-length encode back to text, e.g. ``"2 inc, 1 sc"``."""
        if not self.stitches:
            return ""
        parts: list[str] = []
        current, count = self.stitches[0], 1
        for st in self.stitches[1:]:
            if st == current:
                count += 1
            else:
                parts.append(f"{count} {current.to_token()}")
                current, count = st, 1
        parts.append(f"{count} {current.to_token()}")
        return ", ".join(parts)

    def __len__(self) -> int:
        return len(self.stitches)

    def __iter__(self) -> Iterator[Stitch]:
        return iter(self.stitches)


@dataclass(frozen=True)
class RowError:
    """One problem found by :meth:`Pattern.validate`."""

    row_index: int
    detail: str

    def __str__(self) -> str:
        return f"row {self.row_index}: {self.detail}"


@dataclass
class ValidationReport:
    """The result of :meth:`Pattern.validate`."""

    ok: bool
    errors: list[RowError] = field(default_factory=list)

    def message(self) -> str:
        """``"valid"``, or a description of the first problem."""
        if self.ok:
            return "valid"
        return str(self.errors[0]) if self.errors else "invalid"

    def raise_if_invalid(self, name: str = "") -> "ValidationReport":
        """Raise :class:`InvalidPatternError` instead of reporting.

        Returns ``self``, so ``pattern.validate().raise_if_invalid()`` chains.
        """
        if not self.ok:
            where = f"{name}: " if name else ""
            raise InvalidPatternError(where + self.message())
        return self

    def __bool__(self) -> bool:
        return self.ok


class Pattern:
    """A crochet pattern: a name and a sequence of :class:`Row`.

    Immutable: :attr:`name` and :attr:`rows` are read-only, so a pattern handed to
    :meth:`to_graph`, the solver and the certifier cannot change identity
    mid-pipeline.  Build a different one with :meth:`from_text` or
    :meth:`from_rows`.

    Parses from and renders back to ``Row N [X st]: a, b, c`` text.  Row headers
    are recomputed rather than read, so stale counts in the source are ignored.
    """

    def __init__(self, name: str = "", rows: Sequence[Row] | None = None):
        self._name = name
        self._rows: tuple[Row, ...] = tuple(rows) if rows else ()

    @property
    def name(self) -> str:
        return self._name

    @property
    def rows(self) -> tuple[Row, ...]:
        return self._rows

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pattern):
            return NotImplemented
        return (self._name, self._rows) == (other._name, other._rows)

    def __hash__(self) -> int:
        return hash((self._name, self._rows))

    # -- construction ------------------------------------------------------
    @classmethod
    def from_text(cls, text: str, name: str = "") -> "Pattern":
        """Parse ``Row N [X st]: a, b, c`` lines.  Labels are not trusted."""
        rows: list[Row] = []
        for line in text.split("\n"):
            if ":" not in line:
                continue
            body = line.split(":", 1)[1]
            stitches: list[Stitch] = []
            for token in body.split(","):
                stitches.extend(Stitch.parse_many(token))
            rows.append(Row(len(rows), stitches))
        return cls(name, rows)

    @classmethod
    def from_rows(cls, rows: Sequence[Sequence[Stitch]], name: str = "") -> "Pattern":
        return cls(name, [Row(i, list(r)) for i, r in enumerate(rows)])

    # -- representation ----------------------------------------------------
    def to_text(self) -> str:
        text = ""
        for row in self.rows:
            text += f"Row {row.index + 1} [{row.stitch_count} st]:  {row.pack()}\n"
        return text

    def __str__(self) -> str:
        return self.to_text()

    def __iter__(self) -> Iterator[Row]:
        return iter(self.rows)

    # -- info -----------------------------------------------------------
    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def stitch_count(self) -> int:
        """Total stitches, i.e. the number of graph nodes."""
        return sum(row.stitch_count for row in self.rows)

    def row_lengths(self) -> list[int]:
        return [row.stitch_count for row in self.rows]

    def validate(self) -> ValidationReport:
        """Check that every row works into exactly the previous row's stitch count.

        Row 0 is the baseline and is not checked.
        """
        errors: list[RowError] = []
        previous: int | None = None
        for row in self.rows:
            if previous is not None and row.parent_slots != previous:
                errors.append(
                    RowError(
                        row.index,
                        f"works into {row.parent_slots} stitches of a {previous}-stitch row",
                    )
                )
            previous = row.stitch_count
        return ValidationReport(not errors, errors)

    # -- topology ----------------------------------------------------------
    def to_graph(self, seed: int = 0) -> "StitchGraph":
        """Build the stitch graph: one node per stitch, plus horizontal edges
        within each row and vertical edges down to the row below.  Every node is
        given a ``pos`` layout guess and a ``weight``.
        """
        graph = nx.Graph()
        rng = random.Random(seed)
        rows: list[int] = []
        stitch = 0

        # Horizontal edges
        for row_index, row in enumerate(self.rows):
            length = row.stitch_count
            rows.extend([row_index] * length)
            for i in range(length):
                graph.add_node(
                    stitch,
                    pos=[i - (length - 1) / 2, row_index + 1, rng.random() * 10],
                    weight=1,
                )
                if i == 0:
                    # A one-stitch row is horizontally isolated: it gets no
                    # self-loop, only its vertical parent edge.
                    if length > 1:
                        graph.add_edge(stitch, stitch + length - 1, weight=1 / (2**row_index))
                else:
                    graph.add_edge(stitch, stitch - 1, weight=1 / (2**row_index))
                stitch += 1

        # Vertical edges: each stitch works into `consumes()` stitches of the
        # row below, starting at the next unconsumed slot of that row.
        parent = 0  # first stitch of the row below still unconsumed
        child = 0  # first stitch of the current row
        for row_index, row in enumerate(self.rows):
            weighting = 1 / (2**row_index)
            if row_index == 0:
                child = row.stitch_count
                continue
            for st in row:
                n = st.repeat
                if st.kind is StitchKind.DEC:
                    # one child absorbs n+1 parents
                    for i in range(n + 1):
                        graph.add_edge(child, parent + i, weight=weighting)
                    child += 1
                    parent += n + 1
                elif st.kind is StitchKind.INC:
                    # n+1 children all work into one parent
                    for i in range(n + 1):
                        graph.add_edge(child + i, parent, weight=weighting)
                    child += n + 1
                    parent += 1
                else:
                    graph.add_edge(child, parent, weight=weighting)
                    child += 1
                    parent += 1
        return StitchGraph(graph, rows)


class StitchGraph:
    """A stitch graph plus the row index of every node.

    All accessors index arrays by node id, so node labels must be exactly
    ``0..n-1``.  That is checked once, here, at construction: ``list(graph.nodes())``
    is *insertion* order, which is not id order even when the labels are right -
    :meth:`Pattern.to_graph` adds the magic-ring wrap edge before the rest of the
    nodes, so ``list(graph.nodes())[:4]`` can be ``[0, 19, 1, 2]``.
    """

    def __init__(self, graph: nx.Graph, rows: Sequence[int] | None = None):
        ids = sorted(graph.nodes())
        if ids != list(range(len(ids))):
            raise UnsolvableGraphError(
                "node labels must be exactly 0..n-1; got "
                f"{ids[:6]}{'...' if len(ids) > 6 else ''}. "
                "Use networkx.convert_node_labels_to_integers first."
            )
        self._graph = graph
        n = graph.number_of_nodes()
        self.rows: list[int] = list(rows) if rows is not None else [0] * n

    @classmethod
    def from_pattern(cls, pattern: Pattern, seed: int = 0) -> "StitchGraph":
        return pattern.to_graph(seed)

    @classmethod
    def from_edges(cls, n: int, edges, rows: Sequence[int] | None = None) -> "StitchGraph":
        """Build directly from an edge list, for imported topology."""
        graph = nx.Graph()
        graph.add_nodes_from(range(n))
        graph.add_edges_from([(int(u), int(v)) for u, v in edges])
        return cls(graph, rows)

    # -- topology ----------------------------------------------------------
    @property
    def n(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def m(self) -> int:
        return self._graph.number_of_edges()

    @property
    def graph(self) -> nx.Graph:
        """The underlying networkx graph."""
        return self._graph

    def node_ids(self) -> list[int]:
        return sorted(self._graph.nodes())

    def edge_array(self) -> np.ndarray:
        """Edges as an ``(m, 2)`` int64 array of node ids."""
        return np.asarray(list(self._graph.edges), dtype=np.int64).reshape(-1, 2)

    def edge_weights(self) -> np.ndarray:
        return np.asarray(
            [d.get("weight", 1.0) for _, _, d in self._graph.edges(data=True)], dtype=float
        )

    def to_networkx(self) -> nx.Graph:
        return self._graph

    # -- coordinates -------------------------------------------------------
    @property
    def has_positions(self) -> bool:
        return self.n > 0 and all("pos" in d for _, d in self._graph.nodes(data=True))

    @property
    def positions(self) -> np.ndarray | None:
        """``(n, 3)`` coordinates indexed by node id, or None if unset."""
        if not self.has_positions:
            return None
        x = np.zeros((self.n, 3), dtype=float)
        for node, data in self._graph.nodes(data=True):
            x[int(node)] = data["pos"]
        return x

    @positions.setter
    def positions(self, x) -> None:
        x = np.asarray(x, dtype=float).reshape(self.n, 3)
        for node in self._graph.nodes:
            # A list, not an array: keeps the graph networkx-serialisable.
            self._graph.nodes[node]["pos"] = x[int(node)].tolist()

    def __len__(self) -> int:
        return self.n

    def __repr__(self) -> str:
        return f"StitchGraph(n={self.n}, m={self.m}, rows={len(set(self.rows))})"
