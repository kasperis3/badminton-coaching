import pytest

from tests.conftest import follow, manual_pairings_form_six_players, start_session

pytestmark = pytest.mark.regression


def _start_and_open_builder(client, players, **kwargs):
    response = start_session(client, players, **kwargs)
    follow(client, response)
    return client.get("/round/edit-pairings", follow_redirects=True)


def test_edit_pairings_opens_builder_from_auto_round(client, six_players):
    builder = _start_and_open_builder(client, six_players, num_courts=2)
    assert builder.status_code == 200
    assert b"Set pairings" in builder.data


def test_manual_pairings_submit_shows_round_without_exploratory_hint(
    client, six_players
):
    _start_and_open_builder(client, six_players, num_courts=2)

    round_page = client.post(
        "/round/pairings",
        data=manual_pairings_form_six_players(),
        follow_redirects=True,
    )
    assert round_page.status_code == 200
    assert b"Round 1 matchups" in round_page.data
    assert b"Exploratory round" not in round_page.data


def test_auto_pairings_from_builder(client, six_players):
    _start_and_open_builder(client, six_players, num_courts=2)

    round_page = client.post("/round/pairings/auto", follow_redirects=True)
    assert round_page.status_code == 200
    assert b"Round 1 matchups" in round_page.data
    assert b"Exploratory round" in round_page.data


def test_edit_pairings_returns_to_builder(client, six_players):
    _start_and_open_builder(client, six_players, num_courts=2)
    client.post("/round/pairings", data=manual_pairings_form_six_players())
    client.get("/round")

    builder = client.get("/round/edit-pairings", follow_redirects=True)
    assert builder.status_code == 200
    assert b"Set pairings" in builder.data


def test_edit_pairings_works_with_no_sit_out(client, four_players):
    """Four players, one court — no sit-out; edit pairings must still open."""
    response = start_session(client, four_players, num_courts=1)
    follow(client, response)
    builder = client.get("/round/edit-pairings", follow_redirects=True)
    assert builder.status_code == 200
    assert b"Set pairings" in builder.data
    assert b"Sitting out" not in builder.data
    assert b"swap them" in builder.data.lower() or b"Tip:" in builder.data
