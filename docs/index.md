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
happens. Each try is a full solve, so use `tries=1` for the fast single-shot path;
the default tries several seeds and keeps the cleanest embedding.

## Where to go next

- [The solver](explanation/solver.md) - how unit-edge embedding works, and why the
  shape prior is load-bearing.
- [Certifying an embedding](explanation/geometry.md) - the min-gap certificate, the
  graded verdicts, and two traps.
- [Growth rate and over-density](explanation/growth-limit.md) - why some patterns
  cannot be embedded cleanly, and what that says about the pattern.
- [API reference](reference/api.md) - every public name.
