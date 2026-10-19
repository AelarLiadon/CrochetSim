"""Presentation: turn a positioned stitch graph into visuals.

Matplotlib PNGs, an interactive matplotlib window, a self-contained plotly HTML
model and the face-coloured view.
"""

import math
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import numpy as np

from .pattern import StitchGraph

__all__ = [
    "Camera",
    "EqualAxes",
    "FaceRenderer",
    "HtmlRenderer",
    "MatplotlibBackend",
    "OverlapHighlight",
    "PngRenderer",
    "RenderStyle",
    "Renderer",
    "SceneModel",
    "Viewer",
    "WindowRenderer",
]


# ---------------------------------------------------------------------------
# value objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Camera:
    """Viewing angles, in degrees.  :data:`Camera.FRONT` and :data:`Camera.SIDE`
    are the two preset cameras."""

    elev: float = 22.0
    azim: float = 30.0

    def eye(self, distance: float = 2.2) -> dict:
        """Unit-sphere eye position, for plotly's ``scene.camera``."""
        el, az = math.radians(self.elev), math.radians(self.azim)
        return {
            "x": distance * math.cos(el) * math.cos(az),
            "y": distance * math.cos(el) * math.sin(az),
            "z": distance * math.sin(el),
        }


Camera.FRONT = Camera(22.0, 30.0)
Camera.SIDE = Camera(66.0, 140.0)


@dataclass(frozen=True)
class RenderStyle:
    """Appearance knobs shared by every renderer."""

    figsize: tuple = (6.2, 6.2)
    linewidth: float = 0.6
    dpi: int = 110
    node_size: float = 2.4
    cmap: str = "viridis"
    edge_color: str = "#8a94a6"
    overlap_color: str = "#ff2d2d"
    background: str = "#0b0d10"


@dataclass(frozen=True)
class OverlapHighlight:
    """Edges to draw in the warning colour.

    ``edge_indices`` index into the scene's edge array, so ``len`` counts edges,
    not close pairs.
    """

    threshold: float = 0.0
    edge_indices: np.ndarray = field(
        default_factory=lambda: np.zeros(0, dtype=np.int64)
    )

    def active(self) -> bool:
        return int(np.size(self.edge_indices)) > 0

    @property
    def count(self) -> int:
        return int(np.size(self.edge_indices))

    @classmethod
    def empty(cls) -> "OverlapHighlight":
        return cls(0.0, np.zeros(0, dtype=np.int64))

    @classmethod
    def from_report(cls, report, threshold: float | None = None) -> "OverlapHighlight":
        """Build from a ``metrics.ProximityReport``, using its ``close_pairs``."""
        pairs = np.asarray(getattr(report, "close_pairs", []), dtype=np.int64)
        pairs = pairs.reshape(-1, 2)
        edges = np.unique(pairs.ravel()) if pairs.size else np.zeros(0, dtype=np.int64)
        if threshold is None:
            thresholds = getattr(report, "thresholds", None) or (0.0,)
            threshold = float(min(thresholds))
        return cls(float(threshold), edges.astype(np.int64))

    def describe(self) -> str:
        if not self.active():
            return "no overlaps highlighted"
        return (f"{self.count} edges closer than {self.threshold:g} to a "
                f"non-adjacent edge")


@dataclass
class SceneModel:
    """Coordinates, edges and the overlap highlight that a renderer draws."""

    x: np.ndarray
    edges: np.ndarray
    node_rows: np.ndarray | None = None
    highlight: OverlapHighlight | None = None
    title: str = ""

    @classmethod
    def from_graph(cls, graph: StitchGraph, x=None, highlight=None,
                   title: str = "") -> "SceneModel":
        """Read coordinates and edges off a :class:`pattern.StitchGraph`.

        Coordinates come from ``graph.positions``, indexed by node id, and must
        already be set.  ``node_rows`` defaults to ``graph.rows``.
        """
        if x is None:
            x = graph.positions
            if x is None:
                raise ValueError(
                    "graph has no positions; solve it first, e.g. "
                    "result = embedding.UnitEdgeSolver().solve(graph); "
                    "graph.positions = result.x"
                )
        x = np.asarray(x, dtype=float).reshape(graph.n, 3)
        rows = np.asarray(graph.rows, dtype=np.int64)
        if rows.shape != (graph.n,):
            rows = None
        return cls(x, graph.edge_array(), rows, highlight, title)

    @property
    def n(self) -> int:
        return len(self.x)

    @property
    def m(self) -> int:
        return len(self.edges)

    @property
    def radius(self) -> np.ndarray:
        return np.linalg.norm(self.x - self.x.mean(0), axis=1)

    def segments(self, pairs=None) -> np.ndarray:
        """``(k, 2)`` node pairs -> one ``(3k, 3)`` array with NaN separators.

        A 3D line trace draws one polyline, so ``m`` disjoint segments become a single
        trace with NaNs interleaved.
        """
        pairs = self.edges if pairs is None else np.asarray(pairs, dtype=np.int64)
        pairs = pairs.reshape(-1, 2)
        pts = np.full((len(pairs), 3, 3), np.nan)
        if len(pairs):
            pts[:, 0, :] = self.x[pairs[:, 0]]
            pts[:, 1, :] = self.x[pairs[:, 1]]
        return pts.reshape(-1, 3)

    def highlight_mask(self) -> np.ndarray:
        """Boolean ``(m,)`` mask of edges taking part in an overlap."""
        mask = np.zeros(self.m, dtype=bool)
        if self.highlight is not None and self.highlight.active():
            mask[np.asarray(self.highlight.edge_indices, dtype=np.int64)] = True
        return mask

    def split_by_highlight(self) -> tuple[np.ndarray, np.ndarray]:
        """``(normal_edges, highlighted_edges)`` as ``(k, 2)`` index pairs."""
        if self.m == 0:
            empty = np.zeros((0, 2), dtype=np.int64)
            return empty, empty
        mask = self.highlight_mask()
        return self.edges[~mask], self.edges[mask]


# ---------------------------------------------------------------------------
# matplotlib backend
# ---------------------------------------------------------------------------
class MatplotlibBackend:
    """Chooses matplotlib's process-global backend.

    Saving a figure needs no display; opening a window needs a GUI backend.  Because
    ``matplotlib.use(force=True)`` closes every open figure, switching is refused
    while any figure is open.
    """

    GUI_BACKENDS: ClassVar[tuple] = ("TkAgg", "QtAgg", "Qt5Agg", "WXAgg", "MacOSX")

    @staticmethod
    @contextmanager
    def activate(interactive: bool = False):
        import matplotlib

        previous = matplotlib.get_backend()
        switched = False

        if interactive:
            if previous.lower() == "agg":
                for candidate in MatplotlibBackend.GUI_BACKENDS:
                    try:
                        matplotlib.use(candidate, force=True)
                        switched = True
                        break
                    except Exception:
                        continue
        else:
            try:
                import matplotlib.pyplot as plt
                busy = bool(plt.get_fignums())
            except Exception:
                busy = True          # cannot tell -> do not risk closing anything
            if previous.lower() != "agg" and not busy:
                try:
                    matplotlib.use("Agg", force=True)
                    switched = True
                except Exception:
                    switched = False

        try:
            yield
        finally:
            # Restore the process-global backend, but never while a figure is
            # still open: a live window belongs to its GUI backend and
            # switching would destroy it.  Once nothing is open (the user
            # closed the window, or the caller rendered and moved on) the
            # backend is put back, so opening a viewer cannot silently change
            # how every later call in the process behaves.
            if switched:
                try:
                    import matplotlib.pyplot as plt
                    live = bool(plt.get_fignums())
                except Exception:
                    live = True          # cannot tell -> do not risk closing anything
                if not live:
                    try:
                        matplotlib.use(previous, force=True)
                    except Exception:
                        pass

    @staticmethod
    def available() -> str:
        import matplotlib
        return matplotlib.get_backend()


# ---------------------------------------------------------------------------
# axis helpers
# ---------------------------------------------------------------------------
class EqualAxes:
    """Make a 3D box cubic, so spheres look spherical."""

    @staticmethod
    def format(ax) -> None:
        """Grid off, tick labels off, xyz axis labels on."""
        ax.grid(False)
        for dim in (ax.xaxis, ax.yaxis, ax.zaxis):
            dim.set_ticks([])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")

    @staticmethod
    def apply(ax, x=None) -> None:
        """Set cube-equal limits, around ``x`` or around the current limits."""
        if x is not None:
            x = np.asarray(x, dtype=float).reshape(-1, 3)
            centre = x.mean(0)
            half = 0.55 * np.abs(x - centre).max() * 1.02
            for setter, c in zip((ax.set_xlim3d, ax.set_ylim3d, ax.set_zlim3d), centre):
                setter(float(c - half), float(c + half))
        else:
            limits = (ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d())
            radius = 0.5 * max(abs(lo[1] - lo[0]) for lo in limits)
            for setter, lo in zip((ax.set_xlim3d, ax.set_ylim3d, ax.set_zlim3d), limits):
                middle = float(np.mean(lo))
                setter(middle - radius, middle + radius)
        ax.set_box_aspect((1, 1, 1))


# ---------------------------------------------------------------------------
# renderers
# ---------------------------------------------------------------------------
class Renderer(ABC):
    """Base class for the three output backends.

    ``render`` returns the path written, or None when it only opened a window.
    """

    @abstractmethod
    def render(self, scene: SceneModel, path=None, style: RenderStyle | None = None,
               camera: Camera | None = None):
        raise NotImplementedError


class PngRenderer(Renderer):
    """Static PNG via matplotlib.

    Uses a bare :class:`matplotlib.figure.Figure` rather than ``pyplot``, so the path
    is safe headless.
    """

    def render(self, scene: SceneModel, path="render.png", style=None,
               camera=None) -> Path:
        style = style or RenderStyle()
        camera = camera or Camera()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with MatplotlibBackend.activate(interactive=False):
            fig = self.figure(scene, style, camera)
            fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
            fig.clear()
        return path

    def figure(self, scene: SceneModel, style=None, camera=None):
        import matplotlib
        from matplotlib.figure import Figure
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers "3d")
        from mpl_toolkits.mplot3d.art3d import Line3DCollection

        style = style or RenderStyle()
        camera = camera or Camera()
        fig = Figure(figsize=style.figsize)
        ax = fig.add_subplot(111, projection="3d")

        segments = np.stack([scene.x[scene.edges[:, 0]], scene.x[scene.edges[:, 1]]],
                            axis=1) if scene.m else np.zeros((0, 2, 3))
        mask = scene.highlight_mask()
        if mask.any():
            colours = np.where(mask[:, None], np.array([[0.85, 0.1, 0.1, 1.0]]),
                               np.array([[0.55, 0.55, 0.55, 1.0]]))
        else:
            depth = segments[:, :, 2].mean(1) if scene.m else np.zeros(0)
            depth = (depth - depth.min()) / max(np.ptp(depth), 1e-9) if scene.m else depth
            colours = matplotlib.colormaps[style.cmap](0.1 + 0.9 * depth)
        if scene.m:
            ax.add_collection3d(Line3DCollection(segments, colors=colours,
                                                 linewidths=style.linewidth))
        ax.scatter(scene.x[:, 0], scene.x[:, 1], scene.x[:, 2], s=3,
                   c=scene.x[:, 2], cmap=style.cmap)
        EqualAxes.apply(ax, scene.x)
        ax.view_init(elev=camera.elev, azim=camera.azim)
        ax.set_axis_off()
        if scene.title:
            ax.set_title(scene.title, fontsize=8.5)
        return fig


class WindowRenderer(Renderer):
    """Interactive matplotlib window: left-drag orbits, right-drag pans, scroll zooms.

    Needs a real GUI backend; under Agg the window cannot be interacted with.
    """

    def render(self, scene: SceneModel, path=None, style=None, camera=None):
        style = style or RenderStyle()
        camera = camera or Camera()
        with MatplotlibBackend.activate(interactive=True):
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Line3DCollection

            fig = plt.figure(figsize=(9.5, 8.5))
            ax = fig.add_subplot(111, projection="3d")

            if scene.m:
                segments = np.stack([scene.x[scene.edges[:, 0]],
                                     scene.x[scene.edges[:, 1]]], axis=1)
                mask = scene.highlight_mask()
                if mask.any():
                    colours = np.where(mask[:, None],
                                       np.array([[0.85, 0.1, 0.1, 1.0]]),
                                       np.array([[0.6, 0.6, 0.6, 1.0]]))
                    widths = np.where(mask, 1.5, 0.5)
                else:
                    depth = segments[:, :, 2].mean(1)
                    depth = (depth - depth.min()) / max(np.ptp(depth), 1e-9)
                    colours, widths = plt.cm.viridis(0.1 + 0.9 * depth), style.linewidth
                ax.add_collection3d(Line3DCollection(segments, colors=colours,
                                                     linewidths=widths))
            ax.scatter(scene.x[:, 0], scene.x[:, 1], scene.x[:, 2], s=4,
                       c=scene.x[:, 2], cmap=style.cmap)
            EqualAxes.apply(ax, scene.x)
            ax.view_init(elev=camera.elev, azim=camera.azim)
            ax.set_axis_off()
            if scene.title:
                ax.set_title(scene.title, fontsize=9)

            if path:
                path = Path(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(path, dpi=style.dpi, bbox_inches="tight")
            print("matplotlib viewer: left-drag orbits, right-drag pans, scroll zooms.")
            print("  (install plotly for a smoother browser viewer: uv add plotly)")
            plt.show()
        return Path(path) if path else None


class HtmlRenderer(Renderer):
    """Self-contained plotly HTML model.

    With ``offline=True`` plotly.js is inlined, so the file opens without network
    access.
    """

    def __init__(self, width: int = 1000, height: int = 820):
        self.width = width
        self.height = height

    def render(self, scene: SceneModel, path="model.html", style=None, camera=None,
               offline: bool = True, open_browser: bool = False) -> Path:
        fig = self.figure(scene, style, camera)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(
            str(path),
            include_plotlyjs=True if offline else "cdn",
            config={"scrollZoom": True, "displaylogo": False,
                        "toImageButtonOptions": {"format": "png", "scale": 2}},
        )
        if open_browser:
            import webbrowser
            # as_uri() gives file:///C:/... ; string concatenation produced
            # file://C:\... which browsers do not reliably resolve on Windows.
            webbrowser.open(path.resolve().as_uri())
        return path

    def figure(self, scene: SceneModel, style=None, camera=None):
        import plotly.graph_objects as go

        style = style or RenderStyle()
        camera = camera or Camera()
        normal, close = scene.split_by_highlight()
        traces = []

        if len(close):
            f = scene.segments(close)
            label = scene.highlight.describe() if scene.highlight else f"{len(close)} edges"
            traces.append(go.Scatter3d(
                x=f[:, 0], y=f[:, 1], z=f[:, 2], mode="lines",
                line={"color": style.overlap_color, "width": 4},
                name=label, hoverinfo="skip"))

        if len(normal):
            f = scene.segments(normal)
            traces.append(go.Scatter3d(
                x=f[:, 0], y=f[:, 1], z=f[:, 2], mode="lines",
                line={"color": style.edge_color, "width": 1.6},
                name=f"{len(normal)} unit edges", hoverinfo="skip"))

        centre = scene.x.mean(0)
        radius = scene.radius
        if scene.node_rows is not None:
            colour, cbar = scene.node_rows.astype(float), "row"
        else:
            colour, cbar = scene.x[:, 2] - centre[2], "height"
        text = [
            f"stitch {i}<br>radius {radius[i]:.3f}<br>height {scene.x[i, 2] - centre[2]:.3f}"
            + (f"<br>row {int(scene.node_rows[i])}" if scene.node_rows is not None else "")
            for i in range(scene.n)
        ]
        traces.append(go.Scatter3d(
            x=scene.x[:, 0], y=scene.x[:, 1], z=scene.x[:, 2], mode="markers",
            marker={"size": style.node_size, "color": colour, "colorscale": "Viridis",
                        "showscale": True, "line": {"width": 0},
                        "colorbar": {"title": {"text": cbar, "side": "right"},
                                      "thickness": 14, "len": 0.6, "x": 0.92}},
            text=text, hovertemplate="%{text}<extra></extra>",
            name=f"{scene.n} stitches"))

        axis = {"showbackground": True, "backgroundcolor": "#101216",
                    "gridcolor": "#2a2f38", "zerolinecolor": "#2a2f38",
                    "showticklabels": False, "title": ""}
        fig = go.Figure(data=traces)
        fig.update_layout(
            title={"text": scene.title, "x": 0.01, "y": 0.97, "font": {"size": 13}},
            scene={"xaxis": axis, "yaxis": axis, "zaxis": axis, "aspectmode": "data",
                       "camera": {"eye": camera.eye()}},
            paper_bgcolor=style.background, font={"color": "#c9d1d9", "size": 11},
            legend={"x": 0.01, "y": 0.01, "bgcolor": "rgba(0,0,0,0.5)", "font": {"size": 10}},
            margin={"l": 0, "r": 0, "t": 52, "b": 0}, width=self.width, height=self.height,
        )
        return fig


class FaceRenderer:
    """Face-coloured 3D view.

    Takes coordinates from the graph and faces from ``metrics.FaceSet``.  Returns the
    number of faces drawn.
    """

    def draw(self, graph: StitchGraph, faces, camera=None, max_size: int = 8,
             title: str = "") -> int:
        x = graph.positions
        if x is None:
            raise ValueError("graph has no positions; solve it before drawing faces")
        face_list = list(getattr(faces, "faces", faces))
        face_list = [f for f in face_list if 3 <= len(f) <= max_size]
        if not face_list:
            raise ValueError(f"no faces with 3..{max_size} nodes to draw")

        camera = camera or Camera()
        with MatplotlibBackend.activate(interactive=True):
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection

            polys = [x[np.asarray(f, dtype=int)] for f in face_list]
            heights = np.array([p.mean(axis=0)[2] for p in polys])

            fig = plt.figure()
            ax = fig.add_subplot(projection="3d")
            colours = plt.cm.viridis(plt.Normalize(heights.min(), heights.max())(heights))
            ax.add_collection(Poly3DCollection(polys, facecolors=colours,
                                               edgecolor="black"))
            EqualAxes.apply(ax, x)
            ax.view_init(elev=camera.elev, azim=camera.azim)
            ax.set_axis_off()
            if title:
                ax.set_title(title, fontsize=8.5)
            plt.show()
        return len(polys)


# ---------------------------------------------------------------------------
# facade
# ---------------------------------------------------------------------------
class Viewer:
    """Coordinates, the overlap measurement and the renderers, in one place."""

    def __init__(self, detector=None, png=None, html=None, window=None):
        self._detector = detector
        self.png = png or PngRenderer()
        self.html = html or HtmlRenderer()
        self.window = window or WindowRenderer()

    # -- measurement -------------------------------------------------------
    def detector(self):
        if self._detector is None:
            from .metrics import SelfIntersectionDetector
            self._detector = SelfIntersectionDetector()
        return self._detector

    def highlight(self, graph: StitchGraph, x=None, mark_close: float = 0.0
                  ) -> OverlapHighlight | None:
        """Edges taking part in a non-adjacent pair closer than ``mark_close``,
        or None when ``mark_close`` is 0.
        """
        if mark_close <= 0:
            return None
        x = graph.positions if x is None else np.asarray(x, dtype=float)
        report = self.detector().proximity(x, graph, thresholds=(mark_close,))
        return OverlapHighlight.from_report(report, mark_close)

    def scene(self, graph: StitchGraph, mark_close: float = 0.0,
              title: str = "") -> SceneModel:
        x = graph.positions
        if x is None:
            raise ValueError(
                "graph has no positions; solve it first, e.g. "
                "result = embedding.UnitEdgeSolver().solve(graph); "
                "graph.positions = result.x"
            )
        return SceneModel.from_graph(graph, x, self.highlight(graph, x, mark_close),
                                     title)

    # -- outputs -----------------------------------------------------------
    def save_png(self, graph: StitchGraph, path, camera=None, mark_close: float = 0.0,
                 title: str = "", style=None) -> Path:
        return self.png.render(self.scene(graph, mark_close, title), path, style, camera)

    def save_html(self, graph: StitchGraph, path, camera=None, mark_close: float = 0.0,
                  title: str = "", open_browser: bool = False) -> Path:
        scene = self.scene(graph, mark_close, title)
        return self.html.render(scene, path, None, camera, open_browser=open_browser)

    def show(self, graph: StitchGraph, camera=None, mark_close: float = 0.0,
             title: str = "", path=None):
        """Open a pannable model in a browser, or a matplotlib window as fallback.

        Writes the standalone HTML and opens its file URI.
        """
        scene = self.scene(graph, mark_close, title)
        try:
            import plotly.graph_objects as _go  # noqa: F401
        except ImportError:
            return self.window.render(scene, None, None, camera)
        import tempfile
        target = (Path(path) if path else
                  Path(tempfile.gettempdir()) / "crochetdesign_viewer.html")
        return self.html.render(scene, target, None, camera, open_browser=True)
