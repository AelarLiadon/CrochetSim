"""The solver's calibrated results, and the guarantees it makes about them."""

import pytest

from embedding import SolverConfig, UnitEdgeSolver
from example_patterns import keys
from golden import GOLDEN, pattern_for, solve
from metrics import Verdict
from pattern import StitchGraph


def test_every_golden_row_is_a_catalogue_pattern():
    known = set(keys())
    assert [g.key for g in GOLDEN if g.key not in known] == []


@pytest.mark.parametrize("golden", GOLDEN, ids=lambda g: g.key)
def test_calibrated_result(golden):
    graph, cert = solve(golden)

    assert graph.n == golden.n
    assert graph.m == golden.m

    # Edge exactness is asserted as a ceiling, not bit-equality: see golden.py.
    assert cert.max_err < golden.max_err_ceiling

    # Geometry, to within the solver's branch-to-branch jitter.
    assert cert.min_nonadjacent == pytest.approx(golden.min_gap, abs=1e-3)
    assert cert.face_intersections == golden.crossings
    assert cert.faces.F == golden.faces
    assert cert.faces.chi == 2
    assert cert.gauss_bonnet_over_2pi == pytest.approx(2.0, abs=1e-6)
    assert cert.verdict is Verdict(golden.verdict)


@pytest.mark.parametrize("golden", GOLDEN, ids=lambda g: g.key)
def test_pattern_is_valid(golden):
    """A valid pattern is the precondition; row 0 is the unchecked baseline."""
    assert pattern_for(golden).validate().ok


def test_solver_does_not_mutate_the_graph():
    """The solver returns coordinates; assigning them is the caller's job."""
    graph = StitchGraph.from_edges(4, [(0, 1), (1, 2), (2, 3)])
    before = graph.graph.number_of_nodes(), graph.graph.number_of_edges()

    result = UnitEdgeSolver().solve(graph)

    assert (graph.graph.number_of_nodes(), graph.graph.number_of_edges()) == before
    assert not graph.has_positions
    assert result.x.shape == (4, 3)
    assert result.max_err < 1e-6  # a 4-node path embeds exactly


def test_to_graph_layout_is_seeded():
    """to_graph jitters the layout with a seeded RNG, so builds must agree."""
    pattern = pattern_for(GOLDEN[0])
    a, b = pattern.to_graph(seed=7), pattern.to_graph(seed=7)
    assert a.n == b.n and a.m == b.m
    assert (a.positions == b.positions).all()
