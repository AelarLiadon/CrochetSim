"""Geometry measurement: proximity, faces, curvature and verdict grading."""

import numpy as np
import pytest

from crochetsim._errors import MissingPositionsError
from crochetsim.metrics import (
    DEFAULT_CLEAN_GAP,
    Certifier,
    CertifyConfig,
    FaceSet,
    SelfIntersectionDetector,
    SurfaceMetrics,
    Verdict,
    edge_lengths,
)
from crochetsim.pattern import StitchGraph


def grid_graph(rows: int, cols: int, spacing: float = 1.0):
    """A flat ``rows x cols`` grid of unit edges: ``(graph, x)``.

    Its outer face has ``2*(rows+cols) - 4`` nodes, which exceeds the default
    ``max_size=8`` for 5x5 and larger, so the boundary face is filtered out of the
    intersection and bending measurements the way the real patch patterns need.
    """
    ids = {(r, c): r * cols + c for r in range(rows) for c in range(cols)}
    edges = []
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                edges.append((ids[(r, c)], ids[(r, c + 1)]))
            if r + 1 < rows:
                edges.append((ids[(r, c)], ids[(r + 1, c)]))
    x = np.zeros((len(ids), 3))
    for (r, c), i in ids.items():
        x[i] = (c * spacing, r * spacing, 0.0)
    return StitchGraph.from_edges(len(ids), edges), x


def two_edges(distance: float):
    """Two disjoint unit edges ``distance`` apart, along +x."""
    x = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                  [0.0, distance, 0.0], [1.0, distance, 0.0]])
    return StitchGraph.from_edges(4, [(0, 1), (2, 3)]), x


# ---------------------------------------------------------------------------
# edges and proximity
# ---------------------------------------------------------------------------
def test_edge_lengths_are_per_edge_norms():
    graph, x = grid_graph(2, 2)
    assert edge_lengths(x, graph.edge_array()) == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert edge_lengths(3 * x, graph.edge_array()) == pytest.approx([3.0] * 4)


def test_proximity_measures_the_gap_between_disjoint_edges():
    graph, x = two_edges(0.5)
    report = SelfIntersectionDetector().proximity(graph, x)

    assert report.min_dist == pytest.approx(0.5, abs=1e-9)
    assert report.counts[0.8] == 1     # the pair sits below 0.8
    assert report.counts[0.5] == 0     # thresholds are strict: count is d < t
    assert report.has_overlap()


def test_proximity_defaults_to_the_graph_positions():
    graph, x = two_edges(0.5)

    with pytest.raises(MissingPositionsError):
        SelfIntersectionDetector().proximity(graph)

    graph.positions = x
    report = SelfIntersectionDetector().proximity(graph)
    assert report.min_dist == pytest.approx(0.5, abs=1e-9)


def test_close_pairs_lists_only_pairs_below_the_smallest_threshold():
    """``close_pairs`` is keyed to the smallest threshold, not to ``clean_gap``."""
    graph, x = two_edges(0.5)
    assert SelfIntersectionDetector().proximity(graph, x).close_pairs.shape == (0, 2)

    graph, x = two_edges(0.4)
    report = SelfIntersectionDetector().proximity(graph, x)
    assert report.counts[0.5] == 1
    assert report.close_pairs.shape == (1, 2)
    assert report.close_pairs[0].tolist() == [0, 1]


def test_proximity_ignores_edges_that_share_a_vertex():
    """Adjacent edges meet at distance 0 and must not be counted as overlap."""
    graph, _ = two_edges(1.0)
    joined = StitchGraph.from_edges(4, [(0, 1), (1, 2), (2, 3)])
    x = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                  [1.0, 1.0, 0.0], [1.0, 2.0, 0.0]])

    report = SelfIntersectionDetector().proximity(joined, x)

    assert not report.has_overlap()
    assert report.min_dist == pytest.approx(1.0, abs=0.05)  # shared vertices excluded
    assert graph.m == 2


def test_thresholds_are_the_count_keys():
    graph, x = two_edges(0.4)
    report = SelfIntersectionDetector().proximity(graph, x, thresholds=(0.3, 0.9))

    assert report.thresholds == (0.3, 0.9)
    assert set(report.counts) == {0.3, 0.9}
    assert report.counts[0.3] == 0
    assert report.counts[0.9] == 1


# ---------------------------------------------------------------------------
# faces and curvature
# ---------------------------------------------------------------------------
def test_faces_of_a_grid_have_euler_characteristic_two():
    graph, _ = grid_graph(5, 5)
    face_set = FaceSet.build(graph)

    assert face_set.available
    assert len(face_set) == 17          # 16 quads plus the outer face
    assert face_set.info.chi == 2
    assert face_set.info.planar is True and face_set.info.connected is True


def test_small_faces_drop_the_boundary():
    graph, _ = grid_graph(5, 5)
    face_set = FaceSet.build(graph)

    small = face_set.small()
    assert len(small) == 16
    assert {len(f) for f in small.faces} == {4}


def test_gauss_bonnet_is_two_for_a_flat_grid():
    """All faces, boundary included, or the sum is meaningless."""
    graph, x = grid_graph(5, 5)
    faces = FaceSet.build(graph).faces

    defects = SurfaceMetrics.angle_defects(x, faces, graph.n)

    assert defects.sum() / (2 * np.pi) == pytest.approx(2.0, abs=1e-9)


def test_normals_and_variation_on_a_flat_grid():
    graph, x = grid_graph(5, 5)
    small = FaceSet.build(graph).small()

    normals, areas = SurfaceMetrics.face_normals(x, small.faces)
    assert normals.shape == (16, 3) and (areas > 0).all()
    assert np.abs(normals[:, 2]).min() > 0.99      # the flat grid is z-aligned

    stats = SurfaceMetrics.normal_variation(graph, x)
    assert stats.n_ok > 0
    assert stats.mean == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# verdict grading
# ---------------------------------------------------------------------------
def test_clean_gap_default_is_the_calibrated_value():
    assert DEFAULT_CLEAN_GAP == 0.8
    assert CertifyConfig().clean_gap == DEFAULT_CLEAN_GAP


def test_a_flat_unit_grid_is_clean():
    graph, x = grid_graph(5, 5)
    cert = Certifier().certify(graph, x)

    assert cert.max_err < 1e-12
    assert cert.min_nonadjacent == pytest.approx(1.0, abs=0.05)
    assert cert.face_intersections == 0
    assert cert.gauss_bonnet_over_2pi == pytest.approx(2.0, abs=1e-9)
    assert cert.verdict is Verdict.CLEAN and cert.is_clean()
    assert "VERDICT: CLEAN" in cert.describe()
    assert "n=25" in cert.describe()


def test_close_but_not_crossing_is_tight():
    graph, x = two_edges(0.7)
    cert = Certifier().certify(graph, x)

    assert cert.verdict is Verdict.TIGHT
    assert not cert.is_clean()
    assert cert.counts[0.8] == 1
    assert "TIGHT" in cert.describe()


def test_coincident_nodes_are_defective():
    graph, x = grid_graph(5, 5)
    x = x.copy()
    x[12] = x[6]                       # pile one stitch onto another

    cert = Certifier().certify(graph, x)

    assert cert.verdict is Verdict.DEFECTIVE
    assert cert.max_err > 1e-6 or cert.min_nonadjacent <= 0.0


def test_face_intersections_detects_two_triangles_through_each_other():
    """Direct kernel test: the vertical triangle pierces the horizontal one."""
    x = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 2.0, 0.0],
                  [1.0, 0.5, -1.0], [1.0, 0.5, 1.0], [0.5, 0.5, 0.0]])
    faces = [[0, 1, 2], [3, 4, 5]]

    hit = SelfIntersectionDetector().face_intersections(x, faces)
    assert hit.crossing_count() == 1
    assert hit.face_pairs.tolist() == [[0, 1]]

    apart = x.copy()
    apart[3:, 1] = 5.0                 # slide the second triangle clear
    assert SelfIntersectionDetector().face_intersections(apart, faces).crossing_count() == 0


def test_a_perturbed_grid_is_defective():
    graph, x = grid_graph(5, 5)
    x = x + np.random.default_rng(3).normal(0.0, 0.35, x.shape)

    cert = Certifier().certify(graph, x)

    assert cert.verdict is Verdict.DEFECTIVE
    assert cert.face_intersections is not None   # faces were available and tested
    assert cert.max_err > 1e-6


def test_clean_gap_is_configurable():
    """The same embedding grades differently under a looser threshold."""
    graph, x = two_edges(0.7)

    assert Certifier().certify(graph, x).verdict is Verdict.TIGHT
    loose = Certifier(CertifyConfig(clean_gap=0.5))
    assert loose.certify(graph, x).verdict is Verdict.CLEAN
