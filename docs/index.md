# CrochetSim

Crochet fabric simulator, turning written crochet patterns into 3d meshes.

Currently supports sc, inc, and dec stitches in rounds.

More features and stitch types will be added in future versions.

## Install

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

`solve` validates the pattern, embeds it, certifies the result and assigns the
coordinates to `solution.graph`. 
Each try is a full solve, so use `tries=1` for the fast single-shot path;
the default tries several seeds and keeps the cleanest embedding.

## Live demo

[**Interactive demo**](demo/index.md) - example patterns, each with a pannable
3D model, its written pattern, and corresponding code.

Red edges mark non-adjacent stitch pairs that come closer than 0.8, and as such
can't cleanly embed.


<!-- 
## Where to go next

- [The solver](explanation/solver.md) - how unit-edge embedding works, and why the
  shape prior is load-bearing.
- [Certifying an embedding](explanation/geometry.md) - the min-gap certificate, the
  graded verdicts, and two traps.
- [Growth rate and over-density](explanation/growth-limit.md) - why some patterns
  cannot be embedded cleanly, and what that says about the pattern.
- [API reference](reference/api.md) - every public name. -->
