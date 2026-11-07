"""Build the interactive demo page for CrochetSim's example patterns.

Writes Markdown plus its assets under ``docs/`` so that MkDocs renders it exactly
like any other documentation page.  The theme owns the entire look - header,
navigation, typography, admonitions, tables - and the models follow the site's
light/dark toggle.

Usage::

    uv run python scripts/build_demo.py
    uv run python scripts/build_demo.py --keys all --tries 4
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import crochetsim as cs
from crochetsim.display import Camera, RenderStyle, Viewer, theme_layout

# Marks edges that are too close together
MARK_CLOSE = 0.8

# Patterns to include
DEFAULT_KEYS = [
    "hyperbolic",
    "sphere-small",
    "sphere-large",
    "tube",
    "bowl",
    "circle",
]

# Verdict -> admonition type
VERDICT_KIND = {"CLEAN": "success", "TIGHT": "warning", "DEFECTIVE": "failure"}

VERDICT_TEXT = {
    "TIGHT": "{pairs} non-adjacent stitch pair(s) come closer than {mark:g} without crossing.",
    "DEFECTIVE": "{pairs} non-adjacent stitch pair(s) come closer than {mark:g}.",
}

# The loader and the stylesheet are hand-written next to the generated page
# rather than emitted here; see docs/demo/demo.js and docs/demo/demo.css.
LOADER = "demo.js"
STYLESHEET = "demo.css"


def _title(key: str) -> str:
    """A heading for an example key; the section anchor stays the key itself."""
    return key.replace("-", " ").capitalize()


def _plain_cell(text: str) -> str:
    """Escape the pipe so a value cannot break out of a Markdown table cell."""
    return text.replace("|", "\\|")


def _escape_json(payload: str) -> str:
    """Make a JSON string safe inside a ``<script type="application/json">`` tag."""
    return payload.replace("<", "\\u003c")


def _theme(style: RenderStyle) -> dict:
    """``theme_layout`` without the paper colour, so the page background shows."""
    layout = theme_layout(style)
    layout["paper_bgcolor"] = "rgba(0,0,0,0)"
    return layout


def build_card(key: str, tries: int, mark_close: float, camera: Camera) -> dict:
    """Solve one example and collect everything the demo needs to render it."""
    example = cs.examples.by_key(key)
    solution = cs.solve(example.text, tries=tries)

    viewer = Viewer()
    scene = viewer.scene(solution.graph, mark_close=mark_close, title="")
    figure = viewer.html.figure(scene, camera=camera)

    # The renderer hardcodes a fixed pixel size and a title; the page owns both.
    figure.update_layout(
        title={"text": ""},
        autosize=True,
        width=None,
        height=None,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
    )

    cert = solution.certificate
    pairs = cert.counts.get(mark_close, 0)
    verdict = cert.verdict.name

    return {
        "key": key,
        "tries": tries,
        "mark_close": mark_close,
        "title": _title(key),
        "description": example.description,
        "pattern": example.text.strip("\n"),
        "figure": figure,
        "verdict": verdict,
        "kind": VERDICT_KIND.get(verdict, "note"),
        "verdict_text": VERDICT_TEXT.get(verdict, "").format(mark=mark_close, pairs=pairs),
        "stats": [
            ("stitches", f"{cert.n}"),
            ("unit edges", f"{cert.m}"),
            ("rows", f"{solution.rows}"),
            ("max |len-1|", f"{cert.max_err:.2e}"),
            ("min non-adjacent gap", f"{cert.min_nonadjacent:.4f}"),
            (f"pairs < {mark_close:g}", f"{pairs}"),
            ("solve time", f"{solution.seconds:.1f}s"),
        ],
    }

def solve_cards(
    keys: list[str], tries: int, mark_close: float, camera: Camera | None = None
) -> list[dict]:
    """Solve each key in turn, announcing progress."""
    camera = camera or Camera()
    cards = []
    for key in keys:
        print(f"solving {key} ...", flush=True)
        cards.append(build_card(key, tries, mark_close, camera))
    return cards

def resolve_keys(parser: argparse.ArgumentParser, spec: str, known: list[str]) -> list[str]:
    """Resolve a ``--keys`` value, or exit with a usage error naming the bad keys."""
    if spec == "all":
        keys = list(known)
    elif spec == "default":
        keys = list(DEFAULT_KEYS)
    else:
        keys = [key.strip() for key in spec.split(",")]
    unknown = [key for key in keys if key not in known]
    if unknown:
        parser.error(f"unknown example(s) {unknown}; known: {', '.join(known)}")
    return keys


# ---------------------------------------------------------------------------
# documentation page
# ---------------------------------------------------------------------------
INTRO = """\
# Interactive demo

This page shows examples of crochet patterns that CrochetSim can solve and render in 3D.

*drag to rotate, scroll to zoom, and hover a stitch for its radius, height and row.*

!!! note "Multiplicity of solutions"

    Patterns are modeled as a flexible shell of fabric,
    as such there are many solutions to the same pattern.
    The demos show one possible solution, which may be partially squished
    like a real piece of crochet.
"""

OUTRO = """\
---

Built by `scripts/build_demo.py` from CrochetSim's built-in example patterns,
rendered with plotly.js {version}.
"""


def _stats_table(stats: list[tuple[str, str]]) -> str:
    """A two-column Markdown table, transposed so it stays narrow on screen."""
    header = " | ".join(_plain_cell(name) for name, _ in stats)
    rule = " | ".join("--:" for _ in stats)
    values = " | ".join(_plain_cell(value) for _, value in stats)
    return f"| {header} |\n| {rule} |\n| {values} |"


def _reproduce(card: dict) -> str:
    """The snippet that regenerates this card, so a reader can check the numbers."""
    key = card["key"]
    return "\n".join(
        [
            "```python",
            "import crochetsim as cs",
            "",
            f'solution = cs.solve(cs.examples.by_key("{key}").text, tries={card["tries"]})',
            "print(solution.describe())",
            f"solution.show(mark_close={card['mark_close']:g})",
            "```",
        ]
    )


def _card_markdown(card: dict, viewport: int) -> str:
    key = card["key"]
    pattern = "\n".join(f"    {line}" for line in card["pattern"].splitlines() if line.strip())
    verdict = [f'!!! {card["kind"]} "{card["verdict"]}"']
    if card["verdict_text"]:
        verdict += ["", f"    {card['verdict_text']}"]
    return "\n".join(
        [
            f"## {card['title']}",
            "",
            card["description"],
            "",
            *verdict,
            "",
            f'<div data-viz="{key}" style="height: {viewport}px"></div>',
            "",
            _stats_table(card["stats"]),
            "",
            _reproduce(card),
            "",
            '??? note "Written pattern"',
            "",
            "    ```text",
            pattern,
            "    ```",
            "",
        ]
    )


def render_markdown(cards: list[dict], mark_close: float, viewport: int) -> str:
    """The page body.  Everything here is a construct the theme already styles."""
    from plotly.offline import get_plotlyjs_version

    body = "\n".join(_card_markdown(card, viewport) for card in cards)
    assets = "\n".join(
        [f'<link rel="stylesheet" href="{STYLESHEET}">']
        + [f'<script src="{name}"></script>' for name in ("plotly.min.js", "figures.js", LOADER)]
    )
    return "\n".join(
        [
            INTRO.format(mark=mark_close),
            body,
            OUTRO.format(version=get_plotlyjs_version()),
            "",
            assets,
            "",
        ]
    )


def render_figures_js(cards: list[dict]) -> str:
    """Every figure, plus one colour overlay per scheme, as a single asset.

    Only the colours differ between schemes, so shipping the traces once and
    overlaying a small theme keeps the page from doubling in size.
    """
    payload = {
        "figures": {card["key"]: json.loads(card["figure"].to_json()) for card in cards},
        "themes": {
            "light": _theme(RenderStyle.LIGHT),
            "dark": _theme(RenderStyle.DARK),
        },
    }
    return "window.crochetsim = " + json.dumps(payload, separators=(",", ":")) + ";\n"


def write_page(cards: list[dict], out_dir: Path, mark_close: float, viewport: int) -> list[Path]:
    """Write the Markdown page plus the assets it loads."""
    for name in (LOADER, STYLESHEET):
        sibling = out_dir / name
        if not sibling.exists():
            raise SystemExit(f"missing {sibling}; the demo page loads it as a sibling")

    from plotly.offline import get_plotlyjs

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in (
        ("index.md", render_markdown(cards, mark_close, viewport)),
        ("figures.js", render_figures_js(cards)),
        ("plotly.min.js", get_plotlyjs()),
    ):
        path = out_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-o",
        "--out",
        default=None,
        help="output directory (default docs/demo), which MkDocs turns into the demo page",
    )
    parser.add_argument(
        "--keys",
        default="default",
        help="'default', 'all', or a comma-separated subset of example keys",
    )
    parser.add_argument("--tries", type=int, default=2, help="solver seeds per pattern")
    parser.add_argument(
        "--mark-close",
        type=float,
        default=MARK_CLOSE,
        help="flag non-adjacent edge pairs closer than this",
    )
    parser.add_argument(
        "--viewport",
        type=int,
        default=560,
        help="height in pixels of each interactive model",
    )
    args = parser.parse_args(argv)

    known = cs.examples.keys()
    keys = resolve_keys(parser, args.keys, known)
    cards = solve_cards(keys, args.tries, args.mark_close)

    out_dir = Path(args.out or "docs/demo")
    written = write_page(cards, out_dir, args.mark_close, args.viewport)
    total = sum(path.stat().st_size for path in written)
    print(
        f"wrote {out_dir}/index.md plus {len(written) - 1} assets "
        f"({total / 1024 / 1024:.1f} MB, {len(cards)} patterns)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
