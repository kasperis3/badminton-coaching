import pytest

from mixer_core import generate_round

from tests.conftest import score_form, start_session

pytestmark = pytest.mark.smoke


def test_imports():
    import app  # noqa: F401
    import mixer_core  # noqa: F401


def test_generate_round_smoke():
    players = [f"P{i}" for i in range(6)]
    ps = {p: 0 for p in players}
    hist = {p: 0 for p in players}
    pairings = generate_round(2, ps, hist, hist, {}, {}, {}, 1, "doubles")
    assert pairings["round_num"] == 1


def test_get_index_smoke(client):
    assert client.get("/").status_code == 200


def test_mini_session_smoke(client):
    players = ["A", "B", "C", "D"]
    response = start_session(client, players, num_courts=1)
    assert response.status_code == 302
    round_page = client.get("/round", follow_redirects=True)
    assert round_page.status_code == 200
    saved = client.post(
        "/round/scores",
        data=score_form(doubles=[(7, 1)]),
        follow_redirects=True,
    )
    assert b"Round 1 saved" in saved.data
