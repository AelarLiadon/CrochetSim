"""The built-in example catalogue and its generators."""

from crochetsim import examples
from crochetsim.examples import (
    CATALOGUE,
    ball,
    ball_even,
    bowl,
    by_key,
    circle,
    hyperbolic,
    keys,
    tube,
)
from crochetsim.pattern import Pattern


def test_circle_is_exported():
    """``circle`` is a public generator, like ``hyperbolic``."""
    assert "circle" in examples.__all__
    assert callable(examples.circle)
    assert circle is examples.circle
    assert "circle" in keys()


def test_circle_generates_a_valid_growing_circle():
    """Each row is 12 groups of (n sc, inc), so the count grows by 12."""
    pattern = Pattern.from_text(circle(4), name="circle")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [12, 24, 36, 48]


def test_hyperbolic_grows_by_the_step():
    """Each row stays valid, so the ``step - 1`` filler stitches are required."""
    pattern = Pattern.from_text(hyperbolic(n_rows=5, start=20, step=4), name="hyp")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [20, 25, 31, 38, 47]


def test_tube_holds_its_circumference():
    """No increases at all, so every row is the same length."""
    pattern = Pattern.from_text(tube(n_rows=6, stitches=12), name="tube")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [12] * 6


def test_bowl_flares_then_runs_straight():
    """A flat base, then walls that keep the last base row's count."""
    pattern = Pattern.from_text(bowl(increase_rows=3, start=6, step=6, wall_rows=2), name="bowl")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [6, 12, 18, 18, 18]


def test_ball_rises_and_falls_symmetrically():
    """The downward mirror drops the equator, whose two rows are already there."""
    pattern = Pattern.from_text(ball(rounds=4), name="ball")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [6, 12, 18, 24, 18, 12, 6]


def test_ball_even_follows_every_increase_row_with_a_plain_one():
    """Pin the profile that was measured: this shape crowds its own stitches."""
    pattern = Pattern.from_text(ball_even(), name="ball-even")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [8, 16, 16, 24, 24, 32, 32, 40, 40, 32, 32, 24, 24, 16, 16, 8]


def test_catalogue_keys_and_lookups_agree():
    assert [example.key for example in CATALOGUE] == keys()
    assert by_key("hyperbolic").text == hyperbolic()
