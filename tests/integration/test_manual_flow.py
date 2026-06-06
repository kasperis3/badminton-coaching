import pytest

from tests.conftest import follow, manual_pairings_form_six_players, start_session

pytestmark = pytest.mark.regression


def test_manual_start_redirects_to_pairings_builder(client, six_players):
    response = start_session(
        client, six_players, num_courts=2, pairing_preference="manual"
    )
    assert response.status_code == 302
    assert "/round/pairings" in response.headers["Location"]

    builder = follow(client, response)
    assert builder.status_code == 200
    assert b"Set pairings" in builder.data


def test_manual_pairings_submit_shows_round_without_exploratory_hint(
    client, six_players
):
    start_session(client, six_players, num_courts=2, pairing_preference="manual")
    client.get("/round/pairings")

    round_page = client.post(
        "/round/pairings",
        data=manual_pairings_form_six_players(),
        follow_redirects=True,
    )
    assert round_page.status_code == 200
    assert b"Round 1 matchups" in round_page.data
    assert b"Exploratory round" not in round_page.data


def test_auto_pairings_from_builder(client, six_players):
    start_session(client, six_players, num_courts=2, pairing_preference="manual")
    client.get("/round/pairings")

    round_page = client.post("/round/pairings/auto", follow_redirects=True)
    assert round_page.status_code == 200
    assert b"Round 1 matchups" in round_page.data
    assert b"Exploratory round" in round_page.data


def test_edit_pairings_returns_to_builder(client, six_players):
    start_session(client, six_players, num_courts=2, pairing_preference="manual")
    client.post("/round/pairings", data=manual_pairings_form_six_players())
    client.get("/round")

    builder = client.get("/round/edit-pairings", follow_redirects=True)
    assert builder.status_code == 200
    assert b"Set pairings" in builder.data
