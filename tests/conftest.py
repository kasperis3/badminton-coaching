import pytest

from app import app as flask_app


class FormDict(dict):
    """Minimal form mapping for parse_manual_pairings unit tests."""

    def get(self, key, default=""):
        return dict.get(self, key, default)


@pytest.fixture
def six_players():
    return ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey"]


@pytest.fixture
def seven_players():
    return ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]


@pytest.fixture
def four_players():
    return ["A", "B", "C", "D"]


@pytest.fixture
def client():
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
    )
    with flask_app.test_client() as test_client:
        yield test_client


def start_session(
    client,
    players,
    num_courts=2,
    competition_mode="doubles",
    game_to=7,
    ranked_pairing_mode="after_three",
):
    response = client.post(
        "/start",
        data={
            "num_courts": str(num_courts),
            "competition_mode": competition_mode,
            "game_to": str(game_to),
            "ranked_pairing_mode": ranked_pairing_mode,
            "players": "\n".join(players),
        },
        follow_redirects=False,
    )
    return response


def manual_pairings_form_six_players():
    return {
        "doubles_0_a1": "Alex",
        "doubles_0_a2": "Jordan",
        "doubles_0_b1": "Sam",
        "doubles_0_b2": "Taylor",
        "singles_0_p1": "Morgan",
        "singles_0_p2": "Casey",
    }


def score_form(doubles=None, singles=None):
    """Build POST body for /round/scores."""
    data = {}
    for i, (a, b) in enumerate(doubles or []):
        data[f"doubles_{i}_a"] = str(a)
        data[f"doubles_{i}_b"] = str(b)
    for i, (p1, p2) in enumerate(singles or []):
        data[f"singles_{i}_p1"] = str(p1)
        data[f"singles_{i}_p2"] = str(p2)
    return data


def follow(client, response):
    return client.get(response.headers["Location"])
