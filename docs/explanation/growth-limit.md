# Growth rate and over-density

Not every written pattern can be embedded cleanly, and the failure is a property
of the pattern rather than of the solver. This page records the measured boundary.

## Growth rate

`crochetsim.examples.hyperbolic(n_rows, start, step)` generates a real hyperbolic
pattern, where `step` is the number of stitches between increases and the
`step - 1` in the generated form is load-bearing:

```
step=4  ->  groups of "3 sc, inc"  ->  +25% stitches per row
```

Measured floor: **+25% per row embeds cleanly, +33% does not.** The extra
circumference has nowhere to go, so the rows are forced into contact.

The naive "every sc, inc" form is worse than a bad embedding - it consumes
`every + 1` parents and produces a non-planar tangle that looks like a solver
failure but is really a malformed pattern. This is why `hyperbolic()` *generates*
its rows instead of pasting text: the counts cannot drift.

## Why some closed patterns fail: they are over-dense

A closed surface whose every edge is length 1 can only hold so many stitches around
its equator. In a unit triangular lattice each vertex owns area `sqrt(3)/2`, so `n`
stitches cover area `sqrt(3)*n/2`, and a sphere of that area has equatorial ring
`2*pi*R = sqrt(2*pi*sqrt(3)*n) = 1.65*sqrt(n)`. So a closed pattern needs

```
largest row  <~  1.65 * sqrt(n)
```

| pattern | max row | 1.65*sqrt(n) | ratio | result |
|---|---|---|---|---|
| `sphere-small` | 15 | 14.1 | 1.06 | clean |
| `sphere-large` | 30 | 28.6 | 1.05 | clean |
| `lathe` | 46 | 51.6 | 0.89 | tight |
| `volume` | 72 | 63.5 | **1.13** | defective |
| `cone` | 320 | 41.6 | **7.70** | defective |

Every clean instance is at ratio <= 1.06; both failures are above 1.13. `volume`
asks for 13% more stitches at its equator than that surface has area to support,
so the surplus has to crumple somewhere - in practice in a band where the bottom
and top caps collide. `cone` doubles every row, so its last row demands a
circumference of 320 stitches at radius 51 while the whole fabric covers area
worth only ~41.

This is a heuristic from five closed instances, not a theorem, and it does **not**
apply to open patches: those absorb extra circumference by ruffling, which is
exactly how the +25%/row hyperbolic patch stays clean at a ratio of 3.73.

## A balloon prior does not rescue an over-dense pattern

If the collapse were merely the bending energy flattening things, the natural fix
would be a **balloon prior**: push every node onto a sphere of radius R. It failed
decisively and *monotonically* on the 1,481-stitch `volume` pattern:

| balloon radius R | crossings |
|---|---|
| 6 | 4098 |
| 8 | 1465 |
| 10 | 300 |
| 11.46 | 142 |
| no balloon (plain bending prior) | 16 |

Edge exactness also rotted to 0.27 at R=11.46. The same prior at the sphere's own
radius *nearly* cleans the healthy `sphere-large` control (0 crossings, min gap
0.795), so the prior is not the culprit: `volume` has no clean configuration near a
sphere at any radius. (These figures come from the multi-seed balloon experiment
recorded in `REFACTOR.md`, hence the baseline of 16 crossings rather than the 84
of the single-seed table in [geometry](geometry.md).)

## The shape prior does not know which shape you meant

`lathe` embeds with zero crossings but comes out a rounded blob with its neck
folded into the interior rather than the intended vase. The solver knows only
"unit edges" plus "smooth", and the vase and the blob both satisfy those.
Selecting the intended branch needs extra input this pipeline does not take:
axial symmetry, target radii, or a silhouette.
