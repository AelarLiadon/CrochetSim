"""Geometry measurement and certification.

Pure functions of coordinates that report faces, edge proximity, face
intersections, normals and curvature.  :class:`SelfIntersectionDetector`,
:class:`SurfaceMetrics` and :class:`Certifier` are the API.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

from ._errors import MissingPositionsError
from .pattern import StitchGraph

__all__ = [
    "DEFAULT_CLEAN_GAP",
    "AngleStats",
    "Certificate",
    "Certifier",
    "CertifyConfig",
    "FaceInfo",
    "FaceSet",
    "IntersectionReport",
    "NormalFieldStats",
    "NormalVariationStats",
    "ProximityReport",
    "SelfIntersectionDetector",
    "SurfaceMetrics",
    "Verdict",
    "edge_lengths",
]

DEFAULT_CLEAN_GAP = 0.8


class Verdict(Enum):
    """How bad an embedding is.  Graded, because "bad" has three real cases."""

    CLEAN = "clean"
    TIGHT = "tight"
    DEFECTIVE = "defective"

    @property
    def description(self) -> str:
        return {
            Verdict.CLEAN: "CLEAN - no self-intersection",
            Verdict.TIGHT: "TIGHT - close edge pairs, but no crossing",
            Verdict.DEFECTIVE: "DEFECTIVE - see min gap / intersections below",
        }[self]


# ---------------------------------------------------------------------------
# value objects
# ---------------------------------------------------------------------------
@dataclass
class AngleStats:
    """Summary of a batch of angles in degrees."""

    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    p90: float = 0.0
    p99: float = 0.0
    max: float = 0.0
    label: str = ""

    @classmethod
    def from_array(cls, a, label: str = "") -> "AngleStats":
        a = np.asarray(a, dtype=float)
        if a.size == 0:
            return cls(count=0, label=label)
        return cls(
            count=int(a.size),
            mean=float(a.mean()),
            median=float(np.median(a)),
            p90=float(np.percentile(a, 90)),
            p99=float(np.percentile(a, 99)),
            max=float(a.max()),
            label=label,
        )

    def __bool__(self) -> bool:
        return self.count > 0


@dataclass
class NormalFieldStats:
    """Bending, measured across edge-adjacent faces and across edges."""

    face_angle: AngleStats
    node_angle: AngleStats


@dataclass
class NormalVariationStats:
    """Normal-field variation from PCA normals."""

    n: int
    n_ok: int
    mean: float = 0.0
    median: float = 0.0
    p90: float = 0.0
    p99: float = 0.0
    max: float = 0.0
    frac_above: dict = field(default_factory=dict)
    nonplanarity_mean: float = 0.0
    angles: np.ndarray | None = None


@dataclass
class FaceInfo:
    """Planarity facts about a graph, and the Euler characteristic if known."""

    n: int
    m: int
    planar: bool | None = None
    connected: bool | None = None
    F: int | None = None
    chi: int | None = None


@dataclass
class ProximityReport:
    """Distances between non-adjacent edges - the rigorous overlap test.

    ``candidates_tested`` counts the pairs that survived pruning and filtering.
    ``close_pairs`` holds the pairs below the smallest threshold; that is a pair
    count, not an edge count, since one pinched edge can appear in many pairs.
    """

    min_dist: float
    counts: dict
    close_pairs: np.ndarray
    n_candidates: int
    n_tested: int
    thresholds: tuple = (0.5, 0.8, 0.95)
    pair_dist: np.ndarray | None = None

    def has_overlap(self) -> bool:
        return any(c > 0 for c in self.counts.values())


@dataclass
class IntersectionReport:
    """Exact triangle-triangle intersections between non-adjacent faces."""

    face_pairs: np.ndarray
    tri_pairs: np.ndarray
    n_candidates: int = 0
    n_tri: int = 0

    def crossing_count(self) -> int:
        return len(self.face_pairs)


@dataclass
class CertifyConfig:
    """Thresholds for :class:`Certifier`."""

    clean_gap: float = DEFAULT_CLEAN_GAP
    thresholds: tuple = (0.5, 0.8, 0.95)


# ---------------------------------------------------------------------------
# faces
# ---------------------------------------------------------------------------
def _planar_faces(graph: nx.Graph, n: int, m: int):
    """Faces of a connected planar graph as node-index cycles.

    Returns ``(faces, info)``, where ``faces`` is None when the graph is not
    connected or not planar and ``info`` carries ``V - E + F``.
    """
    info = FaceInfo(n=n, m=m, planar=None, connected=None)
    if not nx.is_connected(graph):
        info.connected = False
        return None, info
    ok, embedding = nx.check_planarity(graph)
    info.planar = bool(ok)
    info.connected = True
    if not ok:
        return None, info
    faces, seen = [], set()
    for u, v in embedding.edges():
        for a, b in ((u, v), (v, u)):
            if (a, b) in seen:
                continue
            face = list(embedding.traverse_face(a, b))
            for i in range(len(face)):
                seen.add((face[i], face[(i + 1) % len(face)]))
            faces.append(face)
    info.F = len(faces)
    info.chi = info.n - info.m + len(faces)
    return faces, info


def _triangulate(faces) -> tuple[np.ndarray, np.ndarray]:
    """Fan-triangulate faces -> ``(tris(K,3), owner(K,))``.

    These faces are quads that are not planar in 3D, so their interior angles do not
    sum to ``(k-2)*pi``; triangulate before measuring angles or curvature.
    """
    tris, owner = [], []
    for fi, f in enumerate(faces):
        for i in range(1, len(f) - 1):
            tris.append((f[0], f[i], f[i + 1]))
            owner.append(fi)
    return np.asarray(tris, dtype=np.int64), np.asarray(owner, dtype=np.int64)


def _boundary_faces(faces, max_size: int = 8):
    """Drop the huge outer/boundary faces.

    Their fan-triangulated slivers manufacture spurious intersections, so use this
    for intersection and bending measurements.  Gauss-Bonnet needs all faces,
    boundary included.
    """
    return [f for f in faces if 3 <= len(f) <= max_size]


class FaceSet:
    """The faces of a stitch graph, with their planarity facts.

    ``faces`` is None when the graph is not connected or not planar; ``info`` says
    which.  Use :meth:`small` for intersection and bending measurements.
    """

    def __init__(self, faces: list[list[int]] | None, info: FaceInfo):
        self.faces = faces
        self.info = info
        self._tris: np.ndarray | None = None
        self._owners: np.ndarray | None = None

    @classmethod
    def build(cls, graph: StitchGraph) -> "FaceSet":
        faces, info = _planar_faces(graph.graph, graph.n, graph.m)
        return cls(faces, info)

    @classmethod
    def of(cls, faces, graph: StitchGraph | None = None) -> "FaceSet":
        """Wrap an existing face list (FaceInfo falls back to counting them)."""
        faces = list(faces)
        n = graph.n if graph is not None else None
        m = graph.m if graph is not None else None
        chi = (n - m + len(faces)) if (n is not None and m is not None and faces) else None
        return cls(faces, FaceInfo(n=n, m=m, planar=None, connected=None,
                                   F=len(faces), chi=chi))

    def small(self, max_size: int = 8) -> "FaceSet":
        return FaceSet(_boundary_faces(self.faces or [], max_size), self.info)

    def triangulate(self) -> tuple[np.ndarray, np.ndarray]:
        if self._tris is None:
            self._tris, self._owners = _triangulate(self.faces or [])
        return self._tris, self._owners

    def triangles(self) -> np.ndarray:
        return self.triangulate()[0]

    def owners(self) -> np.ndarray:
        return self.triangulate()[1]

    @property
    def available(self) -> bool:
        return bool(self.faces)

    def __len__(self) -> int:
        return len(self.faces or [])

    def __bool__(self) -> bool:
        return self.available

    def __repr__(self) -> str:
        sizes = sorted({len(f) for f in (self.faces or [])})
        kind = "unavailable" if not self.available else f"sizes {sizes}"
        return f"FaceSet({len(self.faces or [])} faces, {kind})"


def _face_list(faces) -> list[list[int]] | None:
    """Accept a FaceSet, a plain face list, or None."""
    if faces is None:
        return None
    if isinstance(faces, FaceSet):
        return faces.faces
    return list(faces)


def edge_lengths(x, edges) -> np.ndarray:
    """Length of every edge, indexed by edge."""
    x = np.asarray(x, dtype=float).reshape(-1, 3)
    edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    return np.linalg.norm(x[edges[:, 0]] - x[edges[:, 1]], axis=1)


# ---------------------------------------------------------------------------
# self-intersection
# ---------------------------------------------------------------------------
def _seg_seg_dist(P1, D1, P2, D2):
    """Vectorised minimum distance between segments ``[P1, P1+D1]``, ``[P2, P2+D2]``.

    Ericson's clamped closest-point algorithm; all arguments are ``(k, 3)``.
    """
    r = P1 - P2
    a = np.einsum("ij,ij->i", D1, D1)
    e = np.einsum("ij,ij->i", D2, D2)
    f = np.einsum("ij,ij->i", D2, r)
    c = np.einsum("ij,ij->i", D1, r)
    b = np.einsum("ij,ij->i", D1, D2)
    denom = a * e - b * b
    eps = 1e-12

    parallel = denom < eps * np.maximum(a * e, eps)
    s = np.clip(np.where(parallel, 0.0, b * f - c * e) / np.where(parallel, 1.0, denom), 0.0, 1.0)
    t = np.clip((b * s + f) / np.maximum(e, eps), 0.0, 1.0)
    s = np.clip((b * t - c) / np.maximum(a, eps), 0.0, 1.0)
    return np.linalg.norm((P1 + s[:, None] * D1) - (P2 + t[:, None] * D2), axis=1)


def _edge_proximity(x, edges, thresholds=(0.5, 0.8, 0.95), faces=None) -> ProximityReport:
    """Distances between NON-adjacent edges - the rigorous overlap test.

    Edges sharing a node are excluded, and when ``faces`` is given so are pairs that
    co-occur in a face.  Pruning a cKDTree on midpoints is lossless because all
    edges have length ~1.
    """
    x = np.asarray(x, dtype=float).reshape(-1, 3)
    edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    P, Q = x[edges[:, 0]], x[edges[:, 1]]
    mid = 0.5 * (P + Q)
    half = np.linalg.norm(Q - P, axis=1) / 2.0

    radius = float(max(thresholds)) + 2.0 * half.max()
    tree = cKDTree(mid)
    cand = np.asarray(sorted(tree.query_pairs(radius)), dtype=np.int64).reshape(-1, 2)
    n_candidates = len(cand)

    if n_candidates:
        i, j = cand[:, 0], cand[:, 1]
        shared = (edges[i][:, :, None] == edges[j][:, None, :]).any(1).any(1)
        i, j = i[~shared], j[~shared]
        if faces is not None and len(i):
            incidence = defaultdict(list)
            for fi, f in enumerate(faces):
                for k in range(len(f)):
                    incidence[frozenset((f[k], f[(k + 1) % len(f)]))].append(fi)
            edge_faces = [set(incidence.get(frozenset(e), ())) for e in edges]
            keep = np.array([not (edge_faces[a] & edge_faces[b])
                             for a, b in zip(i, j, strict=True)], dtype=bool)
            i, j = i[keep], j[keep]
        d = _seg_seg_dist(P[i], Q[i] - P[i], P[j], Q[j] - P[j]) if len(i) else np.zeros(0)
    else:
        i, j, d = np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0)

    close = d < float(min(thresholds)) if len(d) else np.zeros(0, bool)
    return ProximityReport(
        min_dist=float(d.min()) if len(d) else float("inf"),
        counts={float(t): int((d < t).sum()) for t in thresholds},
        close_pairs=(np.stack([i[close], j[close]], 1) if close.any()
                     else np.zeros((0, 2), np.int64)),
        n_candidates=int(n_candidates),
        n_tested=len(i),
        thresholds=tuple(float(t) for t in thresholds),
        pair_dist=d,
    )


def _segment_triangle_hit(p0, p1, t0, t1, t2, eps=1e-9):
    """Vectorised Moller-Trumbore: does segment p0-p1 hit triangle t0t1t2?"""
    d = p1 - p0
    e1, e2 = t1 - t0, t2 - t0
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(a) > 1e-14
    f = 1.0 / np.where(ok, a, 1.0)
    s = p0 - t0
    u = f * np.einsum("ij,ij->i", s, h)
    ok &= (u > -eps) & (u < 1 + eps)
    q = np.cross(s, e1)
    v = f * np.einsum("ij,ij->i", d, q)
    ok &= (v > -eps) & (u + v < 1 + eps)
    t = f * np.einsum("ij,ij->i", e2, q)
    ok &= (t > -eps) & (t < 1 + eps)
    return ok


def _coplanar_triangle_overlap(P, Q, eps=1e-7):
    """2D separating-axis test for coplanar triangles (P, Q are (K, 3, 2))."""
    def axes(T):
        e = np.roll(T, -1, axis=1) - T
        a = np.stack([-e[..., 1], e[..., 0]], axis=-1)
        norm = np.linalg.norm(a, axis=-1, keepdims=True)
        return a / np.where(norm > 0, norm, 1.0)

    A = np.concatenate([axes(P), axes(Q)], axis=1)
    pp = np.einsum("kij,kaj->kai", P, A)
    qq = np.einsum("kij,kaj->kai", Q, A)
    separated = (pp.max(2) < qq.min(2) - eps) | (qq.max(2) < pp.min(2) - eps)
    return ~separated.any(1)


def _face_intersections(x, faces, skip_shared_vertex=True) -> IntersectionReport:
    """Exact triangle-triangle intersections between non-adjacent faces.

    Candidate pairs come from a cKDTree on triangle centroids, then an AABB reject,
    then Moller-Trumbore in both directions with a coplanar fallback.  Faces sharing
    a node are skipped.
    """
    x = np.asarray(x, dtype=float).reshape(-1, 3)
    tris, owner = _triangulate(faces)
    empty = np.zeros((0, 2), np.int64)
    if len(tris) == 0:
        return IntersectionReport(empty, empty, 0, 0)

    P = x[tris]
    centroids = P.mean(1)
    radius = np.linalg.norm(P - centroids[:, None, :], axis=2).max(1)
    tree = cKDTree(centroids)
    cand = np.asarray(sorted(tree.query_pairs(2.0 * radius.max())), dtype=np.int64).reshape(-1, 2)
    n_candidates = len(cand)

    if n_candidates:
        i, j = cand[:, 0], cand[:, 1]
        if skip_shared_vertex:
            same = (tris[i][:, :, None] == tris[j][:, None, :]).any(1).any(1)
            i, j = i[~same], j[~same]
        lo_i, hi_i = P[i].min(1), P[i].max(1)
        lo_j, hi_j = P[j].min(1), P[j].max(1)
        keep = (lo_i <= hi_j + 1e-9).all(1) & (lo_j <= hi_i + 1e-9).all(1)
        i, j = i[keep], j[keep]

        hits = np.zeros(len(i), dtype=bool)
        A, B = P[i], P[j]
        for k in range(3):
            hits |= _segment_triangle_hit(A[:, k], A[:, (k + 1) % 3], B[:, 0], B[:, 1], B[:, 2])
            hits |= _segment_triangle_hit(B[:, k], B[:, (k + 1) % 3], A[:, 0], A[:, 1], A[:, 2])

        remaining = ~hits
        if remaining.any():
            Ar, Br = A[remaining], B[remaining]
            nA = np.cross(Ar[:, 1] - Ar[:, 0], Ar[:, 2] - Ar[:, 0])
            nB = np.cross(Br[:, 1] - Br[:, 0], Br[:, 2] - Br[:, 0])
            nA /= np.maximum(np.linalg.norm(nA, axis=1), 1e-300)[:, None]
            nB /= np.maximum(np.linalg.norm(nB, axis=1), 1e-300)[:, None]
            parallel = np.abs(np.einsum("ij,ij->i", nA, nB)) > 1 - 1e-6
            coplanar = parallel & (np.abs(np.einsum("ij,ij->i", Ar[:, 0] - Br[:, 0], nA)) < 1e-6)
            if coplanar.any():
                n = nA[coplanar][0]
                t = np.array([0.0, 0.0, 1.0])
                if abs(n @ t) > 0.9:
                    t = np.array([1.0, 0.0, 0.0])
                u = np.cross(n, t)
                u /= np.linalg.norm(u)
                v = np.cross(n, u)
                def project(Q):
                    return np.stack([Q @ u, Q @ v], axis=-1)
                hits[np.where(remaining)[0][coplanar]] = _coplanar_triangle_overlap(
                    project(Ar[coplanar]), project(Br[coplanar])
                )
        tri_pairs = np.stack([i[hits], j[hits]], 1)
    else:
        tri_pairs = np.zeros((0, 2), np.int64)

    if len(tri_pairs):
        face_pairs = np.unique(
            np.sort(np.stack([owner[tri_pairs[:, 0]], owner[tri_pairs[:, 1]]], 1), axis=1), axis=0
        )
    else:
        face_pairs = np.zeros((0, 2), np.int64)
    return IntersectionReport(face_pairs, tri_pairs, int(n_candidates), len(tris))


class SelfIntersectionDetector:
    """The two independent self-intersection tests.

    :meth:`proximity` is the rigorous one and needs no faces;
    :meth:`face_intersections` depends on face extraction.
    """

    def proximity(self, x, graph: StitchGraph, faces=None,
                  thresholds=(0.5, 0.8, 0.95)) -> ProximityReport:
        return _edge_proximity(x, graph.edge_array(), thresholds=thresholds,
                               faces=_face_list(faces))

    def face_intersections(self, x, faces, skip_shared_vertex: bool = True) -> IntersectionReport:
        return _face_intersections(x, _face_list(faces) or [], skip_shared_vertex)


# ---------------------------------------------------------------------------
# normals and curvature
# ---------------------------------------------------------------------------
def _face_normals(x, faces):
    """Newell normals and areas.  Newell is the right choice for non-planar n-gons."""
    x = np.asarray(x, dtype=float).reshape(-1, 3)
    N = np.zeros((len(faces), 3))
    for fi, f in enumerate(faces):
        V = x[f]
        W = np.roll(V, -1, axis=0)
        N[fi] = [
            np.sum((V[:, 1] - W[:, 1]) * (V[:, 2] + W[:, 2])),
            np.sum((V[:, 2] - W[:, 2]) * (V[:, 0] + W[:, 0])),
            np.sum((V[:, 0] - W[:, 0]) * (V[:, 1] + W[:, 1])),
        ]
    area = 0.5 * np.linalg.norm(N, axis=1)
    norm = np.linalg.norm(N, axis=1)
    return N / np.where(norm > 0, norm, 1.0)[:, None], area


def _node_normals(x, faces, n, N=None, area=None):
    """Area-weighted mean of the incident face normals, normalised."""
    if N is None:
        N, area = _face_normals(x, faces)
    acc = np.zeros((n, 3))
    for fi, f in enumerate(faces):
        w = N[fi] * area[fi]
        for v in f:
            acc[v] += w
    norm = np.linalg.norm(acc, axis=1)
    return acc / np.where(norm > 0, norm, 1.0)[:, None]


def _angles_between(A, B):
    cos = np.einsum("ij,ij->i", A, B) / np.maximum(
        np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1), 1e-300
    )
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def _angle_defects(x, faces, n):
    """Discrete Gaussian curvature ``2*pi - sum(incident face angles)``.

    Summed over all nodes this equals ``2*pi*chi`` (Gauss-Bonnet), but only after
    triangulating and only if the boundary face is included.
    """
    x = np.asarray(x, dtype=float).reshape(-1, 3)
    total = np.zeros(n)
    for f in faces:
        V = x[f]
        a = V - np.roll(V, 1, axis=0)
        b = V - np.roll(V, -1, axis=0)
        cos = np.einsum("ij,ij->i", a, b) / np.maximum(
            np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-300
        )
        np.add.at(total, f, np.arccos(np.clip(cos, -1.0, 1.0)))
    return 2 * np.pi - total


def _pca_normals(graph: nx.Graph, x, ring: int = 1):
    """Per-node normals from the smallest eigenvector of the 1-ring covariance.

    O(n) and needs no face extraction.  Orientations are propagated over a BFS
    spanning tree; the sign ambiguity does not affect the ``|cos|`` statistic.
    """
    n = graph.number_of_nodes()
    x = np.asarray(x, dtype=float).reshape(n, 3)
    neighbours = [np.array(sorted({v for v in graph[u]} | {u})) for u in range(n)]
    if ring >= 2:
        neighbours = [np.array(sorted({w for v in b for w in graph[v]} | set(b)))
                      for b in neighbours]

    N = np.zeros((n, 3))
    lam = np.zeros((n, 3))
    ok = np.zeros(n, dtype=bool)
    for u in range(n):
        P = x[neighbours[u]]
        if len(P) < 3:
            continue
        Q = P - P.mean(0)
        w, V = np.linalg.eigh(Q.T @ Q / len(P))
        N[u] = V[:, 0]
        lam[u] = w
        ok[u] = True

    if ok.any():
        seen = np.zeros(n, dtype=bool)
        start = int(np.argmax(ok))
        seen[start] = True
        stack = [start]
        while stack:
            u = stack.pop()
            for v in graph[u]:
                if not seen[v]:
                    if ok[v] and ok[u] and np.dot(N[u], N[v]) < 0:
                        N[v] = -N[v]
                    seen[v] = True
                    stack.append(v)
    return N, lam, ok


class SurfaceMetrics:
    """Normals, bending and curvature.  Pure functions of coordinates and faces."""

    @staticmethod
    def face_normals(x, faces) -> tuple[np.ndarray, np.ndarray]:
        return _face_normals(x, _face_list(faces) or [])

    @staticmethod
    def node_normals(x, faces, n, N=None, area=None) -> np.ndarray:
        return _node_normals(x, _face_list(faces) or [], n, N, area)

    @staticmethod
    def angle_defects(x, faces, n) -> np.ndarray:
        """Discrete Gaussian curvature.  Triangulates internally, so it is safe on
        faces that are already triangles.
        """
        tris, _ = _triangulate(_face_list(faces) or [])
        return _angle_defects(x, tris, n)

    @staticmethod
    def normal_field_variation(graph: StitchGraph, x, faces) -> NormalFieldStats:
        """Discrete bending: normal angle across edge-adjacent faces and nodes.

        The mean varies with mesh density; compare the tail statistics
        (``p99``/``max``) across meshes.
        """
        faces = _face_list(faces) or []
        N, area = _face_normals(x, faces)
        incidence = defaultdict(list)
        for fi, f in enumerate(faces):
            for i in range(len(f)):
                incidence[frozenset((f[i], f[(i + 1) % len(f)]))].append(fi)
        pairs = [v for v in incidence.values() if len(v) == 2]
        face_angles = (_angles_between(N[[p[0] for p in pairs]], N[[p[1] for p in pairs]])
                       if pairs else np.zeros(0))
        NN = _node_normals(x, faces, graph.n, N, area)
        E = graph.edge_array()
        node_angles = _angles_between(NN[E[:, 0]], NN[E[:, 1]])
        return NormalFieldStats(
            face_angle=AngleStats.from_array(face_angles, "adjacent-face normal angle (deg)"),
            node_angle=AngleStats.from_array(node_angles, "adjacent-node normal angle (deg)"),
        )

    @staticmethod
    def pca_normals(graph: StitchGraph, x, ring: int = 1):
        return _pca_normals(graph.graph, x, ring=ring)

    @staticmethod
    def normal_variation(graph: StitchGraph, x, ring: int = 1,
                         thresholds=(20, 30, 45, 60)) -> NormalVariationStats:
        """Normal-field variation over edges, via PCA normals.  ``|cos|`` used."""
        n = graph.n
        N, lam, ok = SurfaceMetrics.pca_normals(graph, x, ring=ring)
        angles = [
            np.degrees(np.arccos(np.clip(abs(np.dot(N[u], N[v])), -1.0, 1.0)))
            for u, v in graph.graph.edges() if ok[u] and ok[v]
        ]
        angles = np.asarray(angles)
        non_planarity = np.array([
            np.sqrt(max(lam[u][0], 0.0) / lam[u].sum()) if ok[u] and lam[u].sum() > 0 else 0.0
            for u in range(n)
        ])
        stats = NormalVariationStats(n=n, n_ok=int(ok.sum()), angles=angles,
                                     nonplanarity_mean=float(non_planarity.mean()))
        if angles.size:
            stats.mean = float(angles.mean())
            stats.median = float(np.median(angles))
            stats.p90 = float(np.percentile(angles, 90))
            stats.p99 = float(np.percentile(angles, 99))
            stats.max = float(angles.max())
            stats.frac_above = {float(t): float((angles > t).mean()) for t in thresholds}
        return stats


# ---------------------------------------------------------------------------
# the certificate
# ---------------------------------------------------------------------------
@dataclass
class Certificate:
    """The measured verdict on one embedding.

    ``face_intersections``, ``gauss_bonnet_over_2pi``, ``normal_face_angle`` and
    ``normal_node_angle`` are None when the graph has no usable face embedding.
    """

    verdict: Verdict
    n: int
    m: int
    max_err: float
    sum_err: float
    min_nonadjacent: float
    counts: dict
    face_intersections: int | None = None
    gauss_bonnet_over_2pi: float | None = None
    normal_face_angle: AngleStats | None = None
    normal_node_angle: AngleStats | None = None
    normal_pca: NormalVariationStats | None = None
    faces: FaceInfo | None = None
    n_candidates: int = 0
    clean_gap: float = DEFAULT_CLEAN_GAP

    def is_clean(self) -> bool:
        return self.verdict is Verdict.CLEAN

    def describe(self) -> str:
        """Render the certificate as lines of text.
        """
        c = self.counts
        lines = [
            (f"n={self.n}  m={self.m}   edges: max|len-1| = {self.max_err:.2e}"
            f"   sum|len-1| = {self.sum_err:.2e}"),
            (f"min non-adjacent edge distance = {self.min_nonadjacent:.4f}"
            f"   (pairs < 0.8: {c.get(0.8, 0)}, < 0.5: {c.get(0.5, 0)},"
            f" < 0.95: {c.get(0.95, 0)})"),
        ]
        if self.face_intersections is not None:
            chi = self.faces.chi if self.faces else None
            F = self.faces.F if self.faces else None
            lines.append(f"face intersections = {self.face_intersections}"
                         f"   Gauss-Bonnet sum/2pi = {self.gauss_bonnet_over_2pi:.6f}"
                         f"   (chi={chi}, {F} faces)")
        npc = self.normal_pca
        if npc is not None and npc.n_ok:
            lines.append(f"normal-field variation (deg): mean={npc.mean:.2f}"
                         f" p99={npc.p99:.2f} max={npc.max:.2f}"
                         f" frac>45={npc.frac_above.get(45.0, 0.0):.3f}")
        n_close = c.get(float(self.clean_gap), 0)
        verdict = self.verdict.description
        if self.verdict is Verdict.TIGHT:
            verdict = f"TIGHT - {n_close} edge pairs below {self.clean_gap}, but no crossing"
        lines.append(f"VERDICT: {verdict}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.describe()


class Certifier:
    """Measures an embedding: edge exactness, self-intersection, curvature."""

    def __init__(self, config: CertifyConfig | None = None):
        self.config = config or CertifyConfig()
        self.detector = SelfIntersectionDetector()

    def certify(self, graph: StitchGraph, x=None, faces=None) -> Certificate:
        """Measure.  Never prints; call :meth:`Certificate.describe` for text."""
        if x is None:
            x = graph.positions
            if x is None:
                raise MissingPositionsError(
                    "graph has no positions; solve it first (UnitEdgeSolver) or pass x="
                )
        x = np.asarray(x, dtype=float)
        n, m = graph.n, graph.m
        E = graph.edge_array()
        d = edge_lengths(x, E)
        thresholds = self.config.thresholds

        prox = self.detector.proximity(x, graph, thresholds=thresholds)
        if faces is None:
            face_set = FaceSet.build(graph)
            all_faces, face_info = face_set.faces, face_set.info
        else:
            all_faces = _face_list(faces)
            face_info = FaceInfo(
                n=n, m=m, F=len(all_faces) if all_faces else 0,
                chi=(n - m + len(all_faces)) if all_faces else None,
            )

        cert = Certificate(
            verdict=Verdict.CLEAN,
            n=n,
            m=m,
            max_err=float(np.abs(d - 1).max()),
            sum_err=float(np.abs(d - 1).sum()),
            min_nonadjacent=prox.min_dist,
            counts=prox.counts,
            faces=face_info,
            n_candidates=prox.n_candidates,
            clean_gap=self.config.clean_gap,
        )

        if all_faces:
            small = _boundary_faces(all_faces)
            cert.face_intersections = self.detector.face_intersections(x, small).crossing_count()
            # ALL faces, boundary included - triangulating only the small ones
            # gives sum/2pi = 97.5 instead of 2.0.
            cert.gauss_bonnet_over_2pi = float(
                SurfaceMetrics.angle_defects(x, all_faces, n).sum() / (2 * np.pi)
            )
            stats = SurfaceMetrics.normal_field_variation(graph, x, small)
            cert.normal_face_angle = stats.face_angle
            cert.normal_node_angle = stats.node_angle
        cert.normal_pca = SurfaceMetrics.normal_variation(graph, x)

        # Graded verdict.  A crossing (face_intersections > 0) or a touching pair
        # (min_nonadjacent <= 0) is real damage.  A few edge pairs just below
        # clean_gap are only a *warning*: stitches converging into a sharp tip
        # legitimately sit at 1/sqrt(2) = 0.707 apart, and no unit-edge fabric can
        # do better there.  So report the severity, don't collapse it to a bool.
        if (cert.max_err >= 1e-6 or cert.min_nonadjacent <= 0.0
                or cert.face_intersections not in (0, None)):
            cert.verdict = Verdict.DEFECTIVE
        elif cert.counts.get(float(self.config.clean_gap), 0):
            cert.verdict = Verdict.TIGHT
        else:
            cert.verdict = Verdict.CLEAN
        return cert
