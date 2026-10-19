# API reference

The curated top-level API is re-exported from the package, so the common path
needs no submodule knowledge:

```python
import crochetsim as cs

cs.solve, cs.Certifier, cs.Pattern, cs.UnitEdgeSolver, cs.examples
```

Renderers, `Camera` and the render styles are deliberately *not* re-exported:
reach them through `crochetsim.display`, which keeps importing the package free of
matplotlib and plotly.

## Facade

The one-call path: pattern text in, positioned certified model out.

::: crochetsim.api

## Pattern domain

Stitches, rows, patterns, and the stitch graph they produce.

::: crochetsim.pattern

## Example data

The built-in pattern texts and the generators.

::: crochetsim.examples

## Measurement

Given coordinates, report exactness, self-intersection and curvature. Never
solves.

::: crochetsim.metrics

## Solver

Find coordinates where every edge has length 1. Never measures its own
correctness.

::: crochetsim.embedding

## Presentation

PNGs, an interactive window, a pannable plotly model and the face-coloured view.
Imports matplotlib and plotly lazily, so anything else can be used headless.

::: crochetsim.display

## Errors

Every error this package raises deliberately.

::: crochetsim._errors
