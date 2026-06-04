import os
import socket
from datetime import timedelta

from flask import Flask, redirect, render_template, request, session, url_for

from mixer_core import (
    COMPETITION_DOUBLES,
    SchedulingError,
    apply_bye_points,
    apply_round_scores,
    bye_points_for_game_to,
    generate_round,
    normalize_competition_mode,
    normalize_game_to,
    record_games_played,
    standings_rows,
    validate_session,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baddy-dev-change-me-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


def parse_players(raw_names):
    names = []
    seen = set()
    for line in raw_names.splitlines():
        name = line.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def session_scoring():
    game_to = normalize_game_to(session.get("game_to"))
    return game_to, bye_points_for_game_to(game_to)


def build_session_snapshot():
    if "players_scores" not in session:
        return None
    return {
        "num_courts": session.get("num_courts"),
        "game_to": session.get("game_to"),
        "competition_mode": session.get("competition_mode", COMPETITION_DOUBLES),
        "players_scores": session.get("players_scores"),
        "games_played": session.get("games_played"),
        "sit_out_history": session.get("sit_out_history"),
        "singles_history": session.get("singles_history"),
        "partner_history": session.get("partner_history"),
        "matchup_history": session.get("matchup_history"),
        "singles_matchup_history": session.get("singles_matchup_history"),
        "round_num": session.get("round_num"),
        "current_pairings": session.get("current_pairings"),
    }


def restore_session_from_payload(data):
    session.permanent = True
    session["num_courts"] = int(data["num_courts"])
    session["game_to"] = normalize_game_to(data.get("game_to"))
    session["competition_mode"] = normalize_competition_mode(data.get("competition_mode"))
    session["players_scores"] = data["players_scores"]
    session["games_played"] = data["games_played"]
    session["sit_out_history"] = data["sit_out_history"]
    session["singles_history"] = data["singles_history"]
    session["partner_history"] = data.get("partner_history", {})
    session["matchup_history"] = data.get("matchup_history", {})
    session["singles_matchup_history"] = data.get("singles_matchup_history", {})
    session["round_num"] = int(data.get("round_num", 1))
    if data.get("current_pairings"):
        session["current_pairings"] = data["current_pairings"]
    else:
        session.pop("current_pairings", None)


@app.route("/")
def index():
    session.clear()
    return render_template("setup.html")


@app.route("/start", methods=["POST"])
def start_session():
    try:
        num_courts = int(request.form.get("num_courts", 0))
    except ValueError:
        num_courts = 0

    game_to = normalize_game_to(request.form.get("game_to"))
    competition_mode = normalize_competition_mode(request.form.get("competition_mode"))
    players = parse_players(request.form.get("players", ""))

    errors = []
    if num_courts < 1:
        errors.append("Enter at least 1 court.")
    if len(players) < 2:
        errors.append("Add at least 2 unique player names.")
    else:
        court_err = validate_session(len(players), num_courts, competition_mode)
        if court_err:
            errors.append(court_err)

    if errors:
        return render_template(
            "setup.html",
            errors=errors,
            num_courts=num_courts or "",
            game_to=game_to,
            competition_mode=competition_mode,
            players=request.form.get("players", ""),
        )

    session.permanent = True
    session["num_courts"] = num_courts
    session["game_to"] = game_to
    session["competition_mode"] = competition_mode
    session["players_scores"] = {name: 0 for name in players}
    session["games_played"] = {name: 0 for name in players}
    session["sit_out_history"] = {name: 0 for name in players}
    session["singles_history"] = {name: 0 for name in players}
    session["partner_history"] = {}
    session["matchup_history"] = {}
    session["singles_matchup_history"] = {}
    session["round_num"] = 1

    return redirect(url_for("round_view"))


@app.route("/session/restore", methods=["POST"])
def restore_session():
    data = request.get_json(silent=True)
    if not data or "players_scores" not in data:
        return {"ok": False, "error": "Invalid session data"}, 400
    try:
        restore_session_from_payload(data)
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "error": "Invalid session data"}, 400
    redirect_to = url_for("round_view")
    if data.get("current_pairings"):
        redirect_to = url_for("round_view")
    return {"ok": True, "redirect": redirect_to}


@app.route("/round")
def round_view():
    if "players_scores" not in session:
        return redirect(url_for("index"))

    game_to, bye_points = session_scoring()
    competition_mode = session.get("competition_mode", COMPETITION_DOUBLES)

    if "current_pairings" not in session:
        try:
            pairings = generate_round(
                session["num_courts"],
                session["players_scores"],
                session["sit_out_history"],
                session["singles_history"],
                session["partner_history"],
                session["matchup_history"],
                session["singles_matchup_history"],
                session["round_num"],
                competition_mode,
            )
        except SchedulingError as e:
            return render_template(
                "setup.html",
                errors=[str(e)],
                num_courts=session["num_courts"],
                game_to=game_to,
                competition_mode=competition_mode,
                players="\n".join(session["players_scores"].keys()),
            )
        apply_bye_points(session["players_scores"], pairings["byes"], bye_points)
        record_games_played(
            session["games_played"],
            pairings["doubles"],
            pairings["singles_matches"],
        )
        session["current_pairings"] = {
            "doubles": pairings["doubles"],
            "singles_matches": pairings["singles_matches"],
            "byes": pairings["byes"],
            "round_num": pairings["round_num"],
            "rankings": pairings["rankings"],
            "use_ranked_pairing": pairings.get("use_ranked_pairing", False),
            "standings": standings_rows(
                session["players_scores"], session["games_played"]
            ),
        }
        session.modified = True

    snapshot = build_session_snapshot()
    return render_template(
        "round.html",
        pairings=session["current_pairings"],
        game_to=game_to,
        bye_points=bye_points,
        competition_mode=competition_mode,
        session_snapshot=snapshot,
    )


@app.route("/round/scores", methods=["POST"])
def submit_scores():
    if "current_pairings" not in session:
        return redirect(url_for("index"))

    game_to, bye_points = session_scoring()
    competition_mode = session.get("competition_mode", COMPETITION_DOUBLES)
    pairings = session["current_pairings"]
    doubles_scores = []
    singles_scores = []
    errors = []

    def parse_score(raw, label):
        try:
            score = int(raw.strip())
        except ValueError:
            errors.append(f"{label}: enter a whole number.")
            return None
        if not 0 <= score <= game_to:
            errors.append(f"{label}: score must be between 0 and {game_to}.")
            return None
        return score

    for i, match in enumerate(pairings["doubles"]):
        court = i + 1
        score_a = parse_score(request.form.get(f"doubles_{i}_a", ""), f"Court {court} team A")
        score_b = parse_score(request.form.get(f"doubles_{i}_b", ""), f"Court {court} team B")
        if score_a is None or score_b is None:
            continue
        doubles_scores.append((score_a, score_b))

    for i, match in enumerate(pairings.get("singles_matches", [])):
        court = len(pairings["doubles"]) + i + 1
        p1, p2 = match
        score_p1 = parse_score(request.form.get(f"singles_{i}_p1", ""), f"Court {court} {p1}")
        score_p2 = parse_score(request.form.get(f"singles_{i}_p2", ""), f"Court {court} {p2}")
        if score_p1 is None or score_p2 is None:
            continue
        singles_scores.append((score_p1, score_p2))

    expected_doubles = len(pairings["doubles"])
    expected_singles = len(pairings.get("singles_matches", []))
    if (
        errors
        or len(doubles_scores) != expected_doubles
        or len(singles_scores) != expected_singles
    ):
        snapshot = build_session_snapshot()
        return render_template(
            "round.html",
            pairings=pairings,
            errors=errors,
            game_to=game_to,
            bye_points=bye_points,
            competition_mode=competition_mode,
            session_snapshot=snapshot,
        )

    apply_round_scores(
        session["players_scores"],
        pairings["doubles"],
        pairings["singles_matches"],
        doubles_scores,
        singles_scores,
    )
    session.pop("current_pairings", None)
    session.modified = True

    snapshot = build_session_snapshot()
    return render_template(
        "between_rounds.html",
        round_num=session["round_num"],
        standings=standings_rows(session["players_scores"], session["games_played"]),
        session_snapshot=snapshot,
    )


@app.route("/round/next", methods=["POST"])
def next_round():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    session["round_num"] = session.get("round_num", 1) + 1
    session.modified = True
    return redirect(url_for("round_view"))


@app.route("/session/end", methods=["POST"])
def end_session():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    standings = standings_rows(session["players_scores"], session["games_played"])
    archive_payload = {
        "game_to": session.get("game_to"),
        "competition_mode": session.get("competition_mode", COMPETITION_DOUBLES),
        "num_courts": session.get("num_courts"),
        "round_num": session.get("round_num"),
        "player_names": list(session["players_scores"].keys()),
        "standings": [
            {"name": n, "score": s, "games": g} for n, s, g in standings
        ],
    }
    session.clear()
    return render_template(
        "standings.html",
        standings=standings,
        archive_payload=archive_payload,
    )


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3333))
    ip = local_ip()
    print(f"\n  Baddy mixer running!")
    print(f"  On this Mac:  http://127.0.0.1:{port}")
    print(f"  On your phone (same Wi‑Fi): http://{ip}:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
