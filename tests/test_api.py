"""The package's public error contract."""

import re
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


# ---------------------------------------------------------------------------
# the public surface
# ---------------------------------------------------------------------------
PUBLIC_API = [
    "Certificate", "Certifier", "CertifyConfig", "CrochetError",
    "EmbeddingOptimiser", "EmbeddingResult", "FaceSet", "InvalidPatternError",
    "MissingDependencyError", "MissingPositionsError", "Pattern",
    "PatternSyntaxError", "Row", "RowError", "SelfIntersectionDetector",
    "Solution", "Solver", "SolverConfig", "Stitch", "StitchGraph", "StitchKind",
    "SurfaceMetrics", "UnitEdgeSolver", "UnknownExampleError",
    "UnsolvableGraphError", "ValidationReport", "Verdict", "certify", "examples",
    "solve",
]


def test_public_surface_is_pinned():
    """Adding to the curated API should be a deliberate edit to this list."""
    assert cs.__all__ == PUBLIC_API


def test_every_public_name_resolves():
    assert [name for name in cs.__all__ if not hasattr(cs, name)] == []


def test_curated_exports_deliberately_omit_the_view_layer():
    assert "display" not in cs.__all__
    assert "Camera" not in cs.__all__
    assert not any(name.startswith("_") for name in cs.__all__)


def test_version_is_a_release_number():
    assert re.fullmatch(r"\d+\.\d+\.\d+", cs.__version__)


def test_solution_exposes_the_whole_result():
    solution = cs.solve(cs.examples.by_key("sphere-small").text, tries=1)

    assert isinstance(solution, cs.Solution)
    assert solution.rows == 7
    assert solution.graph.n == 73
    assert solution.seed == 3          # the configured default, not 0
    assert solution.is_clean == solution.certificate.is_clean()
    assert solution.x.shape == (73, 3)
    assert "VERDICT" in solution.describe()


def test_solve_refuses_an_invalid_pattern_before_solving():
    with pytest.raises(cs.InvalidPatternError):
        cs.solve("Row 1: 2 sc\nRow 2: 3 sc\n")


def test_solve_rejects_anything_that_is_not_a_pattern():
    with pytest.raises(TypeError):
        cs.solve(123)


def test_solve_honours_an_explicit_seed():
    text = cs.examples.by_key("sphere-small").text
    assert cs.solve(text, tries=1, seed=7).seed == 7


def test_certify_measures_without_solving():
    solution = cs.solve(cs.examples.by_key("sphere-small").text, tries=1)
    again = cs.certify(solution.graph)
    assert again.verdict is solution.certificate.verdict


# ---------------------------------------------------------------------------
# import weight
# ---------------------------------------------------------------------------
HEAVY = ("matplotlib", "plotly", "mpl_toolkits")
CORE_MODULES = ["crochetsim", "crochetsim.api", "crochetsim.pattern",
                "crochetsim.metrics", "crochetsim.embedding", "crochetsim.examples"]


def loaded_heavy_modules(module: str) -> str:
    """What a fresh interpreter has in ``sys.modules`` after importing ``module``."""
    code = (f"import sys, importlib; importlib.import_module({module!r}); "
            f"print(sorted(m for m in {HEAVY!r} if m in sys.modules))")
    done = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.mark.parametrize("module", CORE_MODULES)
def test_core_imports_pull_in_no_gui_toolkit(module):
    """Nothing below display may draw, so a core install works headless."""
    assert loaded_heavy_modules(module) == "[]"


def test_even_display_imports_without_a_toolkit():
    """Every module is importable headless; only *rendering* needs a toolkit.

    display.py imports matplotlib and plotly inside methods, so importing the
    renderers is free.  This is the runtime half of the "nothing below display
    draws" rule, which no import contract can express.
    """
    assert loaded_heavy_modules("crochetsim.display") == "[]"


RENDER_PROBE = textwrap.dedent("""
    import pathlib, sys, tempfile
    import crochetsim as cs
    from crochetsim.display import Viewer

    heavy = ("matplotlib", "plotly")
    solution = cs.solve(cs.examples.by_key("sphere-small").text, tries=1)
    print("solved", [m for m in heavy if m in sys.modules])

    Viewer().save_png(solution.graph, pathlib.Path(tempfile.mkdtemp()) / "a.png")
    print("rendered", [m for m in heavy if m in sys.modules])
""")


def test_rendering_is_what_pulls_the_toolkit_in():
    done = subprocess.run([sys.executable, "-c", RENDER_PROBE],
                          capture_output=True, text=True, check=True)
    solved, rendered = done.stdout.strip().splitlines()

    assert solved == "solved []", solved          # solving needs no view extras
    assert "matplotlib" in rendered, rendered     # drawing does


def test_installed_metadata_matches_the_package_version():
    """``__version__`` is the single source; hatchling reads it at build time."""
    from importlib.metadata import version

    assert version("crochetsim") == cs.__version__
