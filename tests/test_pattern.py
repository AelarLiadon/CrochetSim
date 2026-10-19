"""The pattern domain: parsing, rendering, validation and immutability."""

import pytest

from crochetsim.examples import CATALOGUE, keys
from crochetsim.pattern import Pattern, Row, Stitch, StitchKind, ValidationReport


def test_stitch_kind_production_and_consumption():
    assert StitchKind.SC.produces() == 1 and StitchKind.SC.consumes() == 1
    assert StitchKind.INC.produces() == 2 and StitchKind.INC.consumes() == 1
    assert StitchKind.DEC.produces() == 1 and StitchKind.DEC.consumes() == 2
    # A repeat is "one stitch of size N": it consumes N+1 parents.
    assert StitchKind.INC.produces(4) == 5
    assert StitchKind.DEC.consumes(4) == 5


def test_parse_many_expands_counts_but_not_sizes():
    assert Stitch.parse_many("2 inc") == [Stitch(StitchKind.INC)] * 2
    assert Stitch.parse_many("inc2") == [Stitch(StitchKind.INC, 2)]
    assert Stitch.parse_many("3") == [Stitch(StitchKind.SC)] * 3
    assert Stitch.parse_many("  ") == []


def test_parse_rejects_unknown_tokens():
    assert StitchKind.try_parse("slst") == (None, None)
    with pytest.raises(ValueError):
        Stitch.parse("slst")
    with pytest.raises(ValueError):
        Stitch.parse_many("x inc")


@pytest.mark.parametrize("example", CATALOGUE, ids=lambda e: e.key)
def test_every_catalogue_pattern_validates(example):
    report = Pattern.from_text(example.text, name=example.key).validate()
    assert isinstance(report, ValidationReport)
    assert report.ok, report.message()


@pytest.mark.parametrize("example", CATALOGUE, ids=lambda e: e.key)
def test_text_round_trip_is_stable(example):
    pattern = Pattern.from_text(example.text, name=example.key)
    again = Pattern.from_text(pattern.to_text(), name=example.key)
    assert again == pattern
    assert again.to_text() == pattern.to_text()


def test_row_headers_are_recomputed_not_trusted():
    """A stale count in the source must not survive parsing."""
    pattern = Pattern.from_text("Row 1 [999 st]: 2 sc\n")
    assert pattern.rows[0].stitch_count == 2
    assert "2 st" in pattern.to_text()


def test_validate_reports_the_offending_row():
    # Row 2 works into 3 stitches of a 2-stitch row.
    pattern = Pattern.from_text("Row 1: 2 sc\nRow 2: 3 sc\n")
    report = pattern.validate()
    assert not report
    assert report.errors[0].row_index == 1
    assert "3 stitches" in report.errors[0].detail
    assert report.message().startswith("row 1:")


def test_first_row_is_the_unchecked_baseline():
    """Row 0 has no row below it, so any baseline count is acceptable."""
    assert Pattern.from_text("Row 1: 7 sc\n").validate().ok


def test_pattern_is_immutable():
    pattern = Pattern.from_text("Row 1: 2 sc\n", name="p")
    assert isinstance(pattern.rows, tuple)
    assert isinstance(pattern.rows[0], Row)
    with pytest.raises(AttributeError):
        pattern.rows = ()
    with pytest.raises(AttributeError):
        pattern.name = "other"
    with pytest.raises(AttributeError):
        pattern.rows[0].stitches = ()


def test_row_coerces_any_sequence_to_a_tuple():
    row = Row(0, [Stitch(StitchKind.SC), Stitch(StitchKind.INC)])
    assert row.stitches == (Stitch(StitchKind.SC), Stitch(StitchKind.INC))
    assert len(row) == 2
    assert list(row) == list(row.stitches)


def test_pattern_equality_is_structural():
    a = Pattern.from_text("Row 1: 2 sc\n", name="p")
    b = Pattern.from_text("Row 1: 2 sc\n", name="p")
    c = Pattern.from_text("Row 1: 2 sc\n", name="q")
    assert a == b and hash(a) == hash(b)
    assert a != c
    assert a != "not a pattern"


def test_catalogue_keys_are_unique_and_known():
    assert len(keys()) == len(set(keys())) == len(CATALOGUE)
