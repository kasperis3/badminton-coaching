import pytest

from tests.conftest import follow, score_form, start_session

pytestmark = pytest.mark.regression


def test_invalid_scores_rerender_round_with_error(client, four_players):
    response = start_session(client, four_players, num_courts=1)
    follow(client, response)

    response = client.post(
        "/round/scores",
        data=score_form(doubles=[(7, 7)]),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Both sides cannot have 7 points" in response.data
    assert b"Round 1 matchups" in response.data


def test_invalid_scores_repopulate_inputs(client, four_players):
    response = start_session(client, four_players, num_courts=1)
    follow(client, response)

    response = client.post(
        "/round/scores",
        data=score_form(doubles=[(7, 7)]),
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.data.decode()
    assert 'name="doubles_0_a"' in html
    assert 'name="doubles_0_b"' in html
    assert 'name="doubles_0_a"' in html and 'value="7"' in html
    assert html.count('value="7"') >= 2


def manual_pairings_form_seven_singles():
    return {
        "sit_out": "P7",
        "singles_0_p1": "P1",
        "singles_0_p2": "P2",
        "singles_1_p1": "P3",
        "singles_1_p2": "P4",
        "singles_2_p1": "P5",
        "singles_2_p2": "P6",
    }


def test_swap_changes_sit_out_on_round_page(client):
    players = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    response = start_session(
        client,
        players,
        num_courts=4,
        competition_mode="singles",
    )
    follow(client, response)
    client.get("/round/edit-pairings", follow_redirects=True)
    client.post("/round/pairings", data=manual_pairings_form_seven_singles())

    before = client.get("/round")
    assert before.status_code == 200
    assert b"Swap with sit-out (P7)" in before.data

    swapped = client.post(
        "/round/swap",
        data={
            "match_kind": "singles",
            "match_index": "0",
            "player_out": "P1",
        },
        follow_redirects=True,
    )
    assert swapped.status_code == 200
    assert b"Swap with sit-out (P1)" in swapped.data


def test_session_restore(client, six_players):
    snapshot = {
        "num_courts": 2,
        "game_to": 7,
        "competition_mode": "doubles",
        "players_scores": {n: 0 for n in six_players},
        "games_played": {n: 0 for n in six_players},
        "sit_out_history": {n: 0 for n in six_players},
        "singles_history": {n: 0 for n in six_players},
        "partner_history": {},
        "matchup_history": {},
        "singles_matchup_history": {},
        "round_num": 1,
    }
    response = client.post("/session/restore", json=snapshot)
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert "/round" in data["redirect"]

    round_page = client.get("/round")
    assert round_page.status_code == 200
