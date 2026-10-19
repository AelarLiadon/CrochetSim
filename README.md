# crochetsim

Turn written crochet patterns into graphs, then embed those graphs in 3D so that
every stitch-to-stitch edge has length exactly 1 - the geometric model of real
crocheted fabric, where each stitch is a fixed-length loop joined to its
neighbours.

## Install

```
pip install crochetsim            # library only; no GUI dependencies
pip install 'crochetsim[view]'    # adds matplotlib and plotly for rendering
```

## Quick start

```python
import crochetsim as cs

solution = cs.solve(cs.examples.by_key("hyperbolic").text)
solution.certificate.is_clean()        # True
print(solution.describe())

solution.save_html("hyperbolic.html")  # needs crochetsim[view]
solution.show()                        # pannable, zoomable model in a browser
```

`solve` validates the pattern, embeds it, certifies the result and assigns the
coordinates to `solution.graph`. It refuses an invalid pattern before any solving
happens. Each try is a full solve, so use `tries=1` for the fast single-shot path
(the default tries several seeds and keeps the cleanest embedding).

Drive the pieces yourself when you want to:

```python
from crochetsim import Certifier, Pattern, UnitEdgeSolver
from crochetsim.display import Camera, Viewer

graph = Pattern.from_text(my_pattern).to_graph()
graph.positions = UnitEdgeSolver().solve(graph).x   # solver returns, caller assigns
print(Certifier().certify(graph).describe())
Viewer().save_png(graph, "renders/model.png", camera=Camera.FRONT, mark_close=0.8)
```

## Layout

Five modules plus a facade, one responsibility each. Dependencies run one way:
`api -> display -> metrics -> pattern`. `pattern` and `_errors` are leaves.

| module | role |
|---|---|
| `crochetsim.pattern` | **domain**: stitches, rows, patterns, and the stitch graph they produce |
| `crochetsim.examples` | **data**: the built-in pattern texts and the hyperbolic/circle generators |
| `crochetsim.metrics` | **measurement**: given coordinates, report exactness, self-intersection, curvature |
| `crochetsim.embedding` | **solver**: find coordinates where every edge has length 1 |
| `crochetsim.display` | **presentation**: PNGs, an interactive window, a pannable plotly model |
| `crochetsim.api` | **facade**: `Solution`, `solve`, `certify` |

Three rules hold this together, and the test suite enforces them: `pattern.py`
imports nothing project-local; the solver never explains its own correctness
(`metrics` measures, `embedding` only solves); and nothing below `display` draws,
so importing `crochetsim` never imports matplotlib or plotly.

## Documentation

- [The solver](docs/explanation/solver.md) - how unit-edge embedding works, and why
  the shape prior is load-bearing.
- [Certifying an embedding](docs/explanation/geometry.md) - the min-gap certificate,
  face extraction, and two traps.
- [Growth rate and over-density](docs/explanation/growth-limit.md) - why some
  patterns cannot be embedded cleanly.

## Development

```
uv sync --extra dev
uv run pytest
```

## Status

0.1.0 is library-only; the command line interface lands in 0.2.0.

Licensed under the GNU Affero General Public License, version 3 or later - see
[LICENSE](LICENSE).
