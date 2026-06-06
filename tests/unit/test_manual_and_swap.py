import pytest

from mixer_core import (
    SchedulingError,
    apply_bye_points,
    apply_sit_out_swap,
    build_court_plan,
    commit_manual_round_start,
    pairings_session_dict,
    parse_manual_pairings,
    reverse_round_start_effects,
)

from tests.conftest import FormDict, manual_pairings_form_six_players

pytestmark = pytest.mark.regression


def test_parse_manual_pairings_six_players(six_players):
    plan = build_court_plan("doubles", 6, 2)
    ps = {n: 0 for n in six_players}
    form = FormDict(manual_pairings_form_six_players())
    pairings = parse_manual_pairings(form, plan, six_players, 1, ps)
    assert len(pairings["doubles"]) == 1
    assert len(pairings["singles_matches"]) == 1
    assert pairings["byes"] == []


def test_parse_manual_pairings_rejects_duplicate(six_players):
    plan = build_court_plan("doubles", 6, 2)
    ps = {n: 0 for n in six_players}
    form = FormDict(manual_pairings_form_six_players())
    form["singles_0_p2"] = "Alex"
    with pytest.raises(SchedulingError):
        parse_manual_pairings(form, plan, six_players, 1, ps)


def test_swap_does_not_change_scores_until_bye():
    pairings = {
        "doubles": [],
        "singles_matches": [("P1", "P2")],
        "byes": ["SIT"],
        "round_num": 1,
    }
    scores = {"P1": 0, "P2": 0, "SIT": 0}
    gp = {"P1": 1, "P2": 1, "SIT": 0}
    so = {"P1": 0, "P2": 0, "SIT": 1}
    updated = apply_sit_out_swap(
        pairings, "singles", 0, "P1", scores, gp, so, 4
    )
    assert updated["byes"] == ["P1"]
    assert scores == {"P1": 0, "P2": 0, "SIT": 0}
    apply_bye_points(scores, updated["byes"], 4)
    assert scores["P1"] == 4
    assert scores["SIT"] == 0


def test_multi_swap_single_bye_at_end():
    pairings = {
        "doubles": [],
        "singles_matches": [("P1", "P2"), ("P3", "P4")],
        "byes": ["SIT"],
        "round_num": 1,
    }
    scores = {p: 0 for p in ["P1", "P2", "P3", "P4", "SIT"]}
    gp = {"P1": 1, "P2": 1, "P3": 1, "P4": 1, "SIT": 0}
    so = {p: 0 for p in scores}
    so["SIT"] = 1

    pairings = apply_sit_out_swap(
        pairings, "singles", 0, "P1", scores, gp, so, 4
    )
    pairings = apply_sit_out_swap(
        pairings, "singles", 1, "P3", scores, gp, so, 4
    )
    assert pairings["byes"] == ["P3"]
    apply_bye_points(scores, pairings["byes"], 4)
    assert scores["P3"] == 4
    assert scores["P1"] == 0
    assert scores["SIT"] == 0


def test_pairings_session_dict_manual_flag(six_players):
    pairings = {
        "doubles": [],
        "singles_matches": [],
        "byes": [],
        "round_num": 1,
        "rankings": [],
        "use_ranked_pairing": False,
    }
    ps = {n: 0 for n in six_players}
    gp = {n: 0 for n in six_players}
    session = pairings_session_dict(pairings, ps, gp, manual_pairings=True)
    assert session["manual_pairings"] is True


def test_commit_and_reverse_manual_round_start(six_players):
    pairings = {
        "doubles": [(("Alex", "Jordan"), ("Sam", "Taylor"))],
        "singles_matches": [("Morgan", "Casey")],
        "byes": [],
        "round_num": 1,
    }
    ps = {n: 0 for n in six_players}
    gp = {n: 0 for n in six_players}
    so = {n: 0 for n in six_players}

    commit_manual_round_start(pairings, ps, gp, so, 4)
    assert gp["Alex"] == 1
    assert all(ps[n] == 0 for n in six_players)

    reverse_round_start_effects(pairings, ps, gp, so, 4)
    assert gp["Alex"] == 0
