from tests.conftest import follow, score_form, start_session


def test_index_returns_200(client):
    assert client.get("/").status_code == 200


def test_auto_session_start_to_round(client, four_players):
    response = start_session(client, four_players, num_courts=1)
    assert response.status_code == 302
    assert "/round" in response.headers["Location"]

    round_page = follow(client, response)
    assert round_page.status_code == 200
    assert b"Round 1 matchups" in round_page.data
    assert b"Court 1 (Doubles)" in round_page.data


def test_auto_session_save_scores_and_next_round(client, four_players):
    response = start_session(client, four_players, num_courts=1)
    follow(client, response)

    saved = client.post(
        "/round/scores",
        data=score_form(doubles=[(7, 3)]),
        follow_redirects=True,
    )
    assert saved.status_code == 200
    assert b"Round 1 saved" in saved.data

    nxt = client.post("/round/next", follow_redirects=True)
    assert nxt.status_code == 200
    assert b"Round 2 matchups" in nxt.data


def test_six_player_doubles_two_courts_full_scores(client, six_players):
    response = start_session(client, six_players, num_courts=2)
    follow(client, response)

    saved = client.post(
        "/round/scores",
        data=score_form(doubles=[(7, 4)], singles=[(7, 2)]),
        follow_redirects=True,
    )
    assert saved.status_code == 200
    assert b"Round 1 saved" in saved.data
