# Certifying an embedding

`Certifier().certify(graph, x)` measures one embedding and grades it. It never
prints and never solves; `Certificate.describe()` is what produces text.

```python
cert = Certifier().certify(graph, x)
print(cert.describe())
```

## The min-gap certificate

The core measurement is the minimum distance between **non-adjacent** edges. A
crossing requires that distance to be 0, so the single number is a rigorous
certificate and does not depend on face extraction. Because every edge has unit
length the candidate pruning is lossless: any pair closer than `delta` must have
midpoints closer than `1 + delta`, so a cKDTree radius query cannot miss one.

Calibration matters. A clean quad mesh's opposite sides sit ~0.84-0.87 apart, so a
gap below 1.0 is *not* evidence of overlap. `DEFAULT_CLEAN_GAP = 0.8` sits below
that band.

## Verdicts are graded, because "bad" has three real cases

| verdict | when |
|---|---|
| `CLEAN` | no edge pair below `clean_gap`, no touching pair, no crossing |
| `TIGHT` | edge pairs below `clean_gap`, but nothing crosses |
| `DEFECTIVE` | max edge error >= 1e-6, a pair at distance <= 0, or face intersections |

`TIGHT` exists because stitches converging into a sharp tip legitimately sit at
`1/sqrt(2) = 0.707` apart, and no unit-edge fabric can do better there. Collapsing
that into a boolean would call a correct sharp feature a failure.

## Calibration: the shipped patterns

Single solve, seed 3, default `clean_gap` of 0.8:

| pattern | n | rows | max row | min gap | pairs < 0.8 | crossings | verdict |
|---|---|---|---|---|---|---|---|
| `sphere-small` | 73 | 7 | 15 | 0.8660 | 0 | 0 | clean |
| `sphere-large` | 300 | 15 | 30 | 0.8630 | 0 | 0 | clean |
| `lathe` | 977 | 37 | 46 | 0.7071 | 3 | 0 | tight |
| `volume` | 1481 | 52 | 72 | 0.0029 | 2402 | 84 | **defective** |
| `cone` | 635 | 7 | 320 | 0.0013 | 3228 | 128 | **defective** |
| `hyperbolic` | 808 | 11 | 175 | 0.8359 | 0 | 0 | clean |

`lathe` is only *tight*: all 3 close pairs sit at rows 35-36, the one place the
pattern closes 3 stitches into 1. Three unit edges meeting at a point are
`1/sqrt(2) = 0.707` apart at their far ends and no unit-edge fabric can do better,
so those 3 pairs are a sharp feature, not damage. Zero crossings.

All six have Euler characteristic 2 and a Gauss-Bonnet sum of exactly `2*pi`.

## Faces

Face extraction goes through `nx.check_planarity` + `traverse_face`
(`metrics.FaceSet.build`), which takes 0.03 s at n=808. `nx.minimum_cycle_basis`
is unusable at this scale: measured at 79 s for n=300 and over 100 s at n=808.

Two asymmetries in how faces are used, both load-bearing:

- **Gauss-Bonnet needs *all* faces, boundary included.** Triangulating only the
  small ones gives `sum/2pi = 97.5` instead of `2.0000`.
- **Intersection testing filters the boundary face out.** Its fan-triangulated
  slivers manufacture spurious crossings.
- `SurfaceMetrics.angle_defects` triangulates internally, because these faces are
  quads that are not planar in 3D and their raw interior angles do not sum to
  `(k-2)*pi`. Passing raw faces to the old free function returned 11.19 instead of
  2.0. Fan-triangulating a triangle is a no-op, so the method is safe either way.

## Two traps worth knowing

**Node insertion order is not node id order.** `Pattern.to_graph` adds the
magic-ring wrap edge `add_edge(0, count-1)` before the later `add_node` calls, so
`list(G.nodes())` comes out as `[0, 19, 1, 2, ...]`. Coordinate arrays must be
indexed by node *id*, never by zipping against `G.nodes()`; mixing the two
silently scrambles the geometry. This is why graph/array conversion is
encapsulated in `StitchGraph`, which validates the canonical `0..n-1` labels at
construction.

**The 3D camera can fake an overlap.** Matplotlib's default `view_init` projects
the front and back lobes of a ruffle onto each other, so a genuinely clean
hyperbolic patch renders as a solid ball. `Camera.FRONT` is `elev=22, azim=30` and
`Camera.SIDE` is `elev=66, azim=140`; every renderer defaults to `FRONT`, and it is
worth checking both before concluding that a result self-intersects.

## Other notes

- The `3D_models/*.gexf` artifacts store topology only, no `pos`; geometry has to
  be regenerated with the solver.
- `scratch/` holds the throwaway experiments behind these conclusions and is
  git-ignored.
