"""The built-in example catalogue and its generators."""

from crochetsim import examples
from crochetsim.examples import CATALOGUE, by_key, circle, hyperbolic, keys
from crochetsim.pattern import Pattern


def test_circle_is_exported():
    """circle is a public generator like hyperbolic, so it belongs in __all__."""
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
    """The 'step - 1' is load-bearing: the naive form tangles the graph."""
    pattern = Pattern.from_text(hyperbolic(n_rows=5, start=20, step=4), name="hyp")
    assert pattern.validate().ok
    assert pattern.row_lengths() == [20, 25, 31, 38, 47]


def test_catalogue_keys_and_lookups_agree():
    assert [example.key for example in CATALOGUE] == keys()
    assert by_key("hyperbolic").text == hyperbolic()
