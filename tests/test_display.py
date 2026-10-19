"""Presentation: scene extraction, overlap highlighting and the renderers."""

import numpy as np
import pytest

from crochetsim._errors import MissingPositionsError
from crochetsim.display import (
    Camera,
    EqualAxes,
    MatplotlibBackend,
    SceneModel,
    Viewer,
    _unique_temp_path,
)
from crochetsim.embedding import UnitEdgeSolver
from crochetsim.examples import by_key
from crochetsim.pattern import Pattern, StitchGraph


@pytest.fixture(scope="module")
def solved() -> StitchGraph:
    """A solved sphere-small: unit edges, min non-adjacent gap 0.866."""
    graph = Pattern.from_text(by_key("sphere-small").text).to_graph()
    graph.positions = UnitEdgeSolver().solve(graph).x
    return graph


def unsolved() -> StitchGraph:
    return StitchGraph.from_edges(4, [(0, 1), (1, 2), (2, 3)])


# ---------------------------------------------------------------------------
# temp files and scenes
# ---------------------------------------------------------------------------
def test_unique_temp_path_never_collides():
    paths = [_unique_temp_path(".html") for _ in range(5)]

    assert len(set(paths)) == 5
    assert all(p.exists() for p in paths)
    assert all(p.name.startswith("crochetsim_") and p.suffix == ".html" for p in paths)
    assert len({p.parent for p in paths}) == 1
    # The whole point: a fixed name let two processes clobber each other.
    assert len({p.name for p in paths}) == 5

    for path in paths:
        path.unlink()


def test_scene_model_reads_positions_and_edges(solved):
    scene = SceneModel.from_graph(solved)

    assert scene.n == solved.n and scene.m == solved.m
    assert scene.x.shape == (solved.n, 3)
    assert scene.node_rows.shape == (solved.n,)
    assert np.array_equal(scene.edges, solved.edge_array())


def test_scene_model_needs_positions():
    with pytest.raises(MissingPositionsError):
        SceneModel.from_graph(unsolved())
    with pytest.raises(MissingPositionsError):
        Viewer().scene(unsolved())


def test_scene_segments_use_nan_separators(solved):
    scene = SceneModel.from_graph(solved)
    segments = scene.segments()

    assert segments.shape == (3 * scene.m, 3)
    assert np.isnan(segments).any()


# ---------------------------------------------------------------------------
# overlap highlighting
# ---------------------------------------------------------------------------
def test_no_mark_close_means_no_highlight(solved):
    assert Viewer().highlight(solved, mark_close=0.0) is None
    assert not SceneModel.from_graph(solved).highlight


def test_a_clean_embedding_highlights_nothing(solved):
    """sphere-small has min gap 0.866, so nothing is closer than 0.8."""
    highlight = Viewer().highlight(solved, mark_close=0.8)

    assert highlight is not None
    assert not highlight.active()
    assert highlight.count == 0
    assert "no overlaps" in highlight.describe()


def test_highlight_edges_are_the_proximity_close_pairs(solved):
    """The renderer must not measure anything the certifier would not."""
    viewer = Viewer()
    report = viewer.detector().proximity(solved, solved.positions, thresholds=(0.9,))
    highlight = viewer.highlight(solved, mark_close=0.9)

    expected = np.unique(report.close_pairs.ravel())
    assert np.array_equal(highlight.edge_indices, expected)
    assert highlight.threshold == 0.9
    assert highlight.count == len(expected)


def test_highlight_splits_the_scene_edge_set(solved):
    highlight = Viewer().highlight(solved, mark_close=0.9)
    scene = SceneModel.from_graph(solved, highlight=highlight)
    normal, close = scene.split_by_highlight()

    assert len(normal) + len(close) == scene.m
    assert len(close) == highlight.count


# ---------------------------------------------------------------------------
# renderers
# ---------------------------------------------------------------------------
def test_png_renders_and_the_two_cameras_differ(solved, tmp_path):
    front = Viewer().save_png(solved, tmp_path / "front.png", camera=Camera.FRONT)
    side = Viewer().save_png(solved, tmp_path / "side.png", camera=Camera.SIDE)

    assert front.exists() and side.exists()
    assert front.stat().st_size > 2_000
    # Both cameras must be checked: the default view can fake an overlap.
    assert front.read_bytes() != side.read_bytes()


def test_png_writes_into_a_missing_directory(solved, tmp_path):
    out = Viewer().save_png(solved, tmp_path / "deep" / "nested" / "a.png")
    assert out.exists()


def test_png_render_leaves_the_matplotlib_backend_alone(solved, tmp_path):
    import matplotlib

    before = matplotlib.get_backend()
    Viewer().save_png(solved, tmp_path / "a.png")
    assert matplotlib.get_backend() == before


def test_equal_axes_makes_a_cubic_box():
    import matplotlib.pyplot as plt

    with MatplotlibBackend.activate(interactive=False):
        figure = plt.figure()
        axes = figure.add_subplot(111, projection="3d")
        EqualAxes.format(axes)
        EqualAxes.apply(axes, np.array([[0.0, 0.0, 0.0], [10.0, 2.0, 5.0]]))

        widths = [lo[1] - lo[0] for lo in (axes.get_xlim3d(), axes.get_ylim3d(), axes.get_zlim3d())]
        assert widths[0] == pytest.approx(widths[1])
        assert widths[1] == pytest.approx(widths[2])
        figure.clear()


def test_html_is_self_contained_and_keeps_the_payload(solved, tmp_path):
    out = Viewer().save_html(solved, tmp_path / "model.html")
    text = out.read_text(encoding="utf-8")

    assert out.stat().st_size > 500_000  # plotly.js is inlined, no CDN
    assert "<html" in text.lower()
    assert "NaN" in text  # segment traces use NaN separators
    assert f"{solved.n} stitches" in text  # the node trace is present
    # Per-node hover text; plotly escapes '<' as \u003c inside the JSON payload.
    assert r"stitch 0\u003cbr\u003eradius" in text
