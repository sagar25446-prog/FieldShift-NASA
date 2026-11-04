import pytest

from fieldshift.global_calendar import Calendar, at_point, sequences


def test_global_coordinates_use_only_the_selected_cell():
    assert "Soybeans" in {c.name for c in at_point(-21, -50)}
    assert "Maize" in {c.name for c in at_point(-25.98, 28.23)}
    assert at_point(0, -140) == ()
    assert at_point(-90, 180) == at_point(-90, -180)
    with pytest.raises(ValueError):
        at_point(91, 1)


def test_cross_year_sequences_wait_for_next_planting_and_keep_species_distinct():
    crops = (Calendar("Winter", "A", 320, 70), Calendar("Early", "B", 65, 160),
             Calendar("Other season", "A", 75, 155))
    options = sequences(crops, 10, 2)
    assert (("Winter", 320, 435), ("Early", 795, 890)) in options
    assert all(row[0][2] < row[1][1] for row in options)
    assert not sequences(crops, 1, 3)
