import random

import pytest

from mixer_core import (
    MAX_SINGLES_GAMES,
    SchedulingError,
    best_singles_pair,
    build_court_plan,
    generate_round,
    record_games_played,
    record_round_history,
    validate_session,
)


def test_validate_session_doubles_six_two_courts():
    assert validate_session(6, 2, "doubles") is None


def test_validate_session_singles_seven_four_courts():
    assert validate_session(7, 4, "singles") is None


def test_validate_session_rejects_too_few_courts():
    assert validate_session(8, 1, "doubles") is not None


def test_build_court_plan_doubles_six_players():
    plan = build_court_plan("doubles", 6, 2)
    assert plan["sit_out_count"] == 0
    assert plan["doubles_count"] == 1
    assert plan["singles_count"] == 1


def test_build_court_plan_singles_seven_players():
    plan = build_court_plan("singles", 7, 4)
    assert plan["sit_out_count"] == 1
    assert plan["singles_count"] == 3


def test_generate_round_doubles_layout():
    players = [f"P{i}" for i in range(6)]
    ps = {p: 0 for p in players}
    hist = {p: 0 for p in players}
    pairings = generate_round(2, ps, hist, hist, {}, {}, {}, 1, "doubles")
    assert len(pairings["doubles"]) == 1
    assert len(pairings["singles_matches"]) == 1
    assert pairings["byes"] == []


def test_generate_round_ranked_pairing_phase():
    players = [f"P{i}" for i in range(6)]
    ps = {p: idx * 10 for idx, p in enumerate(players)}
    hist = {p: 0 for p in players}
    random.seed(42)
    r1 = generate_round(2, ps, hist, hist, {}, {}, {}, 1, "doubles")
    r4 = generate_round(2, ps, hist, hist, {}, {}, {}, 4, "doubles")
    assert r1["use_ranked_pairing"] is False
    assert r4["use_ranked_pairing"] is True


def test_record_games_played_rejects_duplicate():
    gp = {"A": 0, "B": 0, "C": 0, "D": 0}
    with pytest.raises(SchedulingError):
        record_games_played(
            gp,
            [(("A", "B"), ("C", "A"))],
            [],
        )


def test_best_singles_pair_falls_back_when_all_at_cap():
    pool = ["P1", "P2", "P3", "P4"]
    singles_history = {p: MAX_SINGLES_GAMES for p in pool}
    pair = best_singles_pair(pool, singles_history, {}, {p: 0 for p in pool}, False)
    assert pair is not None
    assert set(pair) <= set(pool)


def test_generate_round_singles_multi_round_no_error():
    players = [f"P{i}" for i in range(7)]
    ps = {p: 0 for p in players}
    sit_out = {p: 0 for p in players}
    singles_hist = {p: 0 for p in players}
    singles_matchup = {}

    for round_num in range(1, 5):
        pairings = generate_round(
            4,
            ps,
            sit_out,
            singles_hist,
            {},
            {},
            singles_matchup,
            round_num,
            "singles",
        )
        assert len(pairings["singles_matches"]) == 3
        assert len(pairings["byes"]) == 1
        record_round_history(pairings, singles_hist, {}, {}, singles_matchup)
