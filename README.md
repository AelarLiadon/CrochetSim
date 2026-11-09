# CrochetSim

Crochet fabric simulator, turning written crochet patterns into 3D meshes.
Currently supports sc, inc, and dec stitches in rounds.
More features and stitch types will be added in future versions.

[**Live interactive demo**](https://aelarliadon.github.io/CrochetSim/demo/) - example
patterns with pannable 3D models.


## Installation

```
pip install crochetsim            # library only; no GUI dependencies
pip install 'crochetsim[view]'    # adds matplotlib and plotly for rendering
```

## Getting Started

```python
import crochetsim as cs

solution = cs.solve(cs.examples.by_key("hyperbolic").text)
solution.certificate.is_clean()        # True
print(solution.describe())

solution.save_html("hyperbolic.html")  # needs crochetsim[view]
solution.show()                        # pannable, zoomable model in a browser
```

The library can also be used piecewise if preferred, or if you're looking to extend functionality.
```python
from crochetsim import Certifier, Pattern, UnitEdgeSolver
from crochetsim.display import Camera, Viewer

graph = Pattern.from_text(my_pattern).to_graph()
graph.positions = UnitEdgeSolver().solve(graph).x
print(Certifier().certify(graph).describe())
Viewer().save_png(graph, "renders/model.png", camera=Camera.FRONT, mark_close=0.8)
```

## Development

```
uv sync --extra dev
uv run pytest
```

Build the interactive demo page + docs :

```
# writes `docs/demo/index.md` and its assets
uv run python scripts/build_demo.py

uv run mkdocs build --strict
```

Or a single self-contained HTML file, which needs no server:

```
uv run python scripts/build_standalone.py --out demo.html
```