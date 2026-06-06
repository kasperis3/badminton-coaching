from mixer_core import (
    apply_bye_points,
    apply_round_scores,
    parse_score_value,
    validate_match_score,
)


def test_validate_match_score_accepts_winner_at_cap():
    assert validate_match_score(7, 3, 7) is None
    assert validate_match_score(7, 0, 7) is None
    assert validate_match_score(2, 7, 7) is None


def test_validate_match_score_rejects_invalid_results():
    assert validate_match_score(7, 7, 7) is not None
    assert validate_match_score(6, 5, 7) is not None
    assert validate_match_score(0, 0, 7) is not None


def test_parse_score_value():
    assert parse_score_value("7") == 7
    assert parse_score_value("  11  ") == 11
    assert parse_score_value("") is None
    assert parse_score_value("-") is None
    assert parse_score_value("7.5") is None
    assert parse_score_value("abc") is None
    assert parse_score_value(None) is None


def test_apply_round_scores_and_bye():
    scores = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    apply_bye_points(scores, ["E"], 4)
    apply_round_scores(
        scores,
        [(("A", "B"), ("C", "D"))],
        [],
        [(7, 3)],
        [],
    )
    assert scores["A"] == 7
    assert scores["B"] == 7
    assert scores["C"] == 3
    assert scores["D"] == 3
    assert scores["E"] == 4
