import random

import pytest

from mixer_core import (
    MAX_SINGLES_GAMES,
    RANKED_MODE_AFTER_THREE,
    RANKED_MODE_NEVER,
    SchedulingError,
    best_singles_pair,
    build_court_plan,
    generate_round,
    normalize_ranked_pairing_mode,
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


def test_generate_round_never_ranked_stays_random():
    players = [f"P{i}" for i in range(6)]
    ps = {p: idx * 10 for idx, p in enumerate(players)}
    hist = {p: 0 for p in players}
    r4 = generate_round(
        2,
        ps,
        hist,
        hist,
        {},
        {},
        {},
        4,
        "doubles",
        RANKED_MODE_NEVER,
    )
    assert r4["use_ranked_pairing"] is False


def test_normalize_ranked_pairing_mode():
    assert normalize_ranked_pairing_mode(None) == RANKED_MODE_AFTER_THREE
    assert normalize_ranked_pairing_mode("bogus") == RANKED_MODE_AFTER_THREE
    assert normalize_ranked_pairing_mode(RANKED_MODE_NEVER) == RANKED_MODE_NEVER
    assert normalize_ranked_pairing_mode(RANKED_MODE_AFTER_THREE) == RANKED_MODE_AFTER_THREE
    assert normalize_ranked_pairing_mode("always") == "always"


def test_should_use_ranked_pairing_modes():
    from mixer_core import should_use_ranked_pairing

    assert should_use_ranked_pairing(4, RANKED_MODE_AFTER_THREE) is True
    assert should_use_ranked_pairing(3, RANKED_MODE_AFTER_THREE) is False
    assert should_use_ranked_pairing(4, RANKED_MODE_NEVER) is False
    assert should_use_ranked_pairing(1, "always") is True
    assert should_use_ranked_pairing(10, "always") is True


def test_sit_out_rotates_after_everyone_has_sat_once():
    from mixer_core import pick_round_sitter

    players = ["A", "B", "C", "D", "E"]
    sit_out_history = {p: 1 for p in players}
    # A highest score, E lowest — old bug would sit E every round
    players_scores = {"A": 50, "B": 40, "C": 30, "D": 20, "E": 10}

    first = pick_round_sitter(players, sit_out_history, players_scores)
    sit_out_history[first] += 1
    second = pick_round_sitter(players, sit_out_history, players_scores)
    assert first == "E"
    assert second != "E"
    assert sit_out_history[second] == 1


def test_sit_out_multi_round_does_not_stuck_on_lowest():
    from mixer_core import assign_round_sitter

    players = ["A", "B", "C", "D", "E"]
    sit_out_history = {p: 0 for p in players}
    players_scores = {"A": 50, "B": 40, "C": 30, "D": 20, "E": 10}
    sitters = []
    for _ in range(10):
        sitting_out = []
        assign_round_sitter(players, sitting_out, sit_out_history, players_scores)
        sitters.append(sitting_out[0])
    # After full rotation, E should not monopolize sits
    assert sitters.count("E") <= 3
    assert len(set(sitters)) == 5


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
