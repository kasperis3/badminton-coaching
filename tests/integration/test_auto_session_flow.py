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


def test_start_session_accepts_random_all_pairing_mode(client, four_players):
    response = start_session(
        client,
        four_players,
        num_courts=1,
        ranked_pairing_mode="never",
    )
    assert response.status_code == 302
    round_page = follow(client, response)
    assert round_page.status_code == 200
    assert b"Exploratory round" in round_page.data
    assert b"Ranked round" not in round_page.data


def test_mid_session_switch_to_random_keeps_exploratory_on_round_4(client, four_players):
    response = start_session(
        client,
        four_players,
        num_courts=1,
        ranked_pairing_mode="after_three",
    )
    follow(client, response)

    for _ in range(3):
        client.post(
            "/round/scores",
            data=score_form(doubles=[(7, 3)]),
            follow_redirects=True,
        )
        client.post(
            "/round/next",
            data={"ranked_pairing_mode": "never"},
            follow_redirects=True,
        )

    round_page = client.get("/round")
    assert round_page.status_code == 200
    assert b"Round 4 matchups" in round_page.data
    assert b"Exploratory round" in round_page.data
    assert b"Ranked round" not in round_page.data


def test_mid_session_switch_to_always_ranks_immediately(client, four_players):
    response = start_session(
        client,
        four_players,
        num_courts=1,
        ranked_pairing_mode="never",
    )
    follow(client, response)

    client.post(
        "/round/scores",
        data=score_form(doubles=[(7, 3)]),
        follow_redirects=True,
    )
    client.post(
        "/round/next",
        data={"ranked_pairing_mode": "always"},
        follow_redirects=True,
    )

    round_page = client.get("/round")
    assert round_page.status_code == 200
    assert b"Round 2 matchups" in round_page.data
    assert b"Ranked round" in round_page.data
