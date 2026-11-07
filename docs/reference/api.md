# API reference

The curated top-level API is re-exported from the package, so the common path
needs no submodule knowledge:

```python
import crochetsim as cs

cs.solve, cs.Certifier, cs.Pattern, cs.UnitEdgeSolver, cs.examples
```

Renderers, `Camera` and the render styles are deliberately *not* re-exported to allow
for a solver-only installation. Reach them through `crochetsim.display`.

## Facade

The full pipeline: pattern text in, positioned certified model out.

::: crochetsim.api

## Pattern domain

Stitches, rows, patterns, and the stitch graph they produce.

::: crochetsim.pattern

## Example data

The built-in pattern texts and the generators.

::: crochetsim.examples

## Measurement

Given coordinates, report exactness, self-intersection and curvature.

::: crochetsim.metrics

## Solver

Solves 3D embeddings of the stitch graphs.

::: crochetsim.embedding

## Presentation

PNGs, an interactive window, a pannable plotly model and the face-coloured view.
Imports matplotlib and plotly lazily, so anything else can be used headless.

::: crochetsim.display

## Errors

Custom errors raised by this package.

::: crochetsim._errors
