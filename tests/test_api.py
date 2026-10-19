"""The package's public error contract."""

import subprocess
import sys
import textwrap

import networkx as nx
import pytest

import crochetsim as cs
from crochetsim.examples import by_key
from crochetsim.metrics import Certifier
from crochetsim.pattern import Pattern, Stitch, StitchGraph

RAISES = [
    (cs.PatternSyntaxError, ValueError),
    (cs.InvalidPatternError, ValueError),
    (cs.UnsolvableGraphError, ValueError),
    (cs.MissingPositionsError, ValueError),
    (cs.MissingDependencyError, ImportError),
    (cs.UnknownExampleError, KeyError),
]


@pytest.mark.parametrize("error,builtin", RAISES, ids=lambda x: getattr(x, "__name__", ""))
def test_every_error_is_a_crochet_error_and_a_builtin(error, builtin):
    assert issubclass(error, cs.CrochetError)
    assert issubclass(error, builtin)


def test_unparsable_stitch_token():
    with pytest.raises(cs.PatternSyntaxError):
        Stitch.parse("slst")
    with pytest.raises(cs.PatternSyntaxError):
        Stitch.parse_many("x inc")


def test_non_canonical_node_labels():
    with pytest.raises(cs.UnsolvableGraphError):
        StitchGraph(nx.Graph([(5, 6)]))


def test_unknown_example_key():
    with pytest.raises(cs.UnknownExampleError):
        by_key("no-such-pattern")


def test_missing_positions_are_named():
    graph = StitchGraph.from_edges(2, [(0, 1)])
    with pytest.raises(cs.MissingPositionsError):
        Certifier().certify(graph)
    from crochetsim.display import SceneModel

    with pytest.raises(cs.MissingPositionsError):
        SceneModel.from_graph(graph)


def test_invalid_pattern_reports_or_raises():
    pattern = Pattern.from_text("Row 1: 2 sc\nRow 2: 3 sc\n")
    report = pattern.validate()
    assert not report
    with pytest.raises(cs.InvalidPatternError):
        report.raise_if_invalid()
    with pytest.raises(cs.InvalidPatternError, match="named pattern"):
        report.raise_if_invalid("named pattern")
    # Chaining: a valid report passes through.
    assert Pattern.from_text("Row 1: 2 sc\n").validate().raise_if_invalid().ok


MISSING_VIEW_PROBE = textwrap.dedent("""
    import sys, importlib.abc

    class Blocker(importlib.abc.MetaPathFinder):
        \"\"\"Pretend matplotlib and plotly are not installed.\"\"\"
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in ("matplotlib", "plotly"):
                raise ImportError(f"No module named {name!r}")
            return None

    sys.meta_path.insert(0, Blocker())

    from crochetsim._errors import MissingDependencyError
    from crochetsim.display import Viewer
    from crochetsim.embedding import UnitEdgeSolver
    from crochetsim.pattern import StitchGraph

    graph = StitchGraph.from_edges(4, [(0, 1), (1, 2), (2, 3)])
    graph.positions = UnitEdgeSolver().solve(graph).x

    calls = {
        "save_png": lambda: Viewer().save_png(graph, "out.png"),
        "save_html": lambda: Viewer().save_html(graph, "out.html"),
        "show": lambda: Viewer().show(graph),
    }
    for label, call in calls.items():
        try:
            call()
        except MissingDependencyError as exc:
            print(f"{label} OK {exc}")
        except BaseException as exc:                      # noqa: BLE001
            print(f"{label} WRONG {type(exc).__name__}: {exc}")
        else:
            print(f"{label} NO-RAISE")
""")


def test_missing_view_dependency_explains_the_extra():
    """Viewer's output methods must name crochetsim[view], not leak ImportError."""
    result = subprocess.run([sys.executable, "-c", MISSING_VIEW_PROBE],
                            capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 3, result.stdout + result.stderr
    for line in lines:
        assert "OK" in line, line
        assert "crochetsim[view]" in line, line
