import os
import socket
from datetime import timedelta

from flask import Flask, redirect, render_template, request, session, url_for

from mixer_core import (
    COMPETITION_DOUBLES,
    PAIRING_AUTO,
    PAIRING_MANUAL,
    RANKED_MODE_AFTER_THREE,
    RANKED_MODE_ALWAYS,
    RANKED_MODE_NEVER,
    SchedulingError,
    apply_bye_points,
    apply_round_scores,
    apply_sit_out_swap,
    build_court_plan,
    bye_points_for_game_to,
    commit_manual_round_start,
    generate_round,
    normalize_competition_mode,
    normalize_game_to,
    normalize_ranked_pairing_mode,
    pairings_session_dict,
    pairings_to_draft,
    parse_manual_pairings,
    parse_score_value,
    record_games_played,
    record_round_history,
    reverse_round_start_effects,
    should_use_ranked_pairing,
    standings_rows,
    validate_match_score,
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


def player_names():
    return list(session["players_scores"].keys())


def build_session_snapshot():
    if "players_scores" not in session:
        return None
    return {
        "num_courts": session.get("num_courts"),
        "game_to": session.get("game_to"),
        "competition_mode": session.get("competition_mode", COMPETITION_DOUBLES),
        "pairing_preference": session.get("pairing_preference"),
        "ranked_pairing_mode": session.get(
            "ranked_pairing_mode", RANKED_MODE_AFTER_THREE
        ),
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
    session["pairing_preference"] = data.get("pairing_preference")
    session["ranked_pairing_mode"] = normalize_ranked_pairing_mode(
        data.get("ranked_pairing_mode")
    )
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


def finalize_auto_pairings(pairings):
    record_games_played(
        session["games_played"],
        pairings["doubles"],
        pairings["singles_matches"],
    )
    session["current_pairings"] = pairings_session_dict(
        pairings, session["players_scores"], session["games_played"]
    )
    session.modified = True


def manual_pairings_context(errors=None):
    competition_mode = session.get("competition_mode", COMPETITION_DOUBLES)
    names = player_names()
    court_plan = build_court_plan(
        competition_mode, len(names), session["num_courts"]
    )
    draft = session.get("pairings_draft") or {"doubles": [], "singles": [], "sit_out": ""}
    return {
        "round_num": session.get("round_num", 1),
        "competition_mode": competition_mode,
        "num_courts": session["num_courts"],
        "players": names,
        "court_plan": court_plan,
        "draft": draft,
        "errors": errors or [],
    }


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
    ranked_pairing_mode = normalize_ranked_pairing_mode(
        request.form.get("ranked_pairing_mode")
    )
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
            ranked_pairing_mode=ranked_pairing_mode,
            players=request.form.get("players", ""),
        )

    session.permanent = True
    session["num_courts"] = num_courts
    session["game_to"] = game_to
    session["competition_mode"] = competition_mode
    session["pairing_preference"] = PAIRING_AUTO
    session["ranked_pairing_mode"] = ranked_pairing_mode
    session["players_scores"] = {name: 0 for name in players}
    session["games_played"] = {name: 0 for name in players}
    session["sit_out_history"] = {name: 0 for name in players}
    session["singles_history"] = {name: 0 for name in players}
    session["partner_history"] = {}
    session["matchup_history"] = {}
    session["singles_matchup_history"] = {}
    session["round_num"] = 1
    session.pop("pairings_draft", None)

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
    elif session.get("pairing_preference") == PAIRING_MANUAL and not data.get("round_num"):
        redirect_to = url_for("manual_pairings_view")
    return {"ok": True, "redirect": redirect_to}


@app.route("/round/pairings", methods=["GET"])
def manual_pairings_view():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    if "current_pairings" in session:
        return redirect(url_for("round_view"))
    return render_template("manual_pairings.html", **manual_pairings_context())


@app.route("/round/pairings", methods=["POST"])
def submit_manual_pairings():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    if "current_pairings" in session:
        return redirect(url_for("round_view"))

    competition_mode = session.get("competition_mode", COMPETITION_DOUBLES)
    names = player_names()
    court_plan = build_court_plan(
        competition_mode, len(names), session["num_courts"]
    )
    game_to, bye_points = session_scoring()

    try:
        pairings = parse_manual_pairings(
            request.form,
            court_plan,
            names,
            session["round_num"],
            session["players_scores"],
        )
    except SchedulingError as e:
        draft = {"sit_out": request.form.get("sit_out", "")}
        draft["doubles"] = []
        draft["singles"] = []
        for i in range(court_plan["doubles_count"]):
            draft["doubles"].append(
                {
                    "a1": request.form.get(f"doubles_{i}_a1", ""),
                    "a2": request.form.get(f"doubles_{i}_a2", ""),
                    "b1": request.form.get(f"doubles_{i}_b1", ""),
                    "b2": request.form.get(f"doubles_{i}_b2", ""),
                }
            )
        for i in range(court_plan["singles_count"]):
            draft["singles"].append(
                {
                    "p1": request.form.get(f"singles_{i}_p1", ""),
                    "p2": request.form.get(f"singles_{i}_p2", ""),
                }
            )
        session["pairings_draft"] = draft
        ctx = manual_pairings_context(errors=[str(e)])
        return render_template("manual_pairings.html", **ctx)

    commit_manual_round_start(
        pairings,
        session["players_scores"],
        session["games_played"],
        session["sit_out_history"],
        bye_points,
    )
    session["current_pairings"] = pairings_session_dict(
        pairings, session["players_scores"], session["games_played"], manual_pairings=True
    )
    session.modified = True
    return redirect(url_for("round_view"))


@app.route("/round/pairings/auto", methods=["POST"])
def auto_pairings_for_round():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    if "current_pairings" in session:
        return redirect(url_for("round_view"))

    competition_mode = session.get("competition_mode", COMPETITION_DOUBLES)
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
            session.get("ranked_pairing_mode", RANKED_MODE_AFTER_THREE),
        )
    except SchedulingError as e:
        return render_template(
            "manual_pairings.html",
            **manual_pairings_context(errors=[str(e)]),
        )

    finalize_auto_pairings(pairings)
    session.pop("pairings_draft", None)
    session.modified = True
    return redirect(url_for("round_view"))


@app.route("/round/edit-pairings")
def edit_pairings():
    if "current_pairings" not in session:
        return redirect(url_for("index"))

    game_to, bye_points = session_scoring()
    pairings = session["current_pairings"]
    reverse_round_start_effects(
        pairings,
        session["players_scores"],
        session["games_played"],
        session["sit_out_history"],
        bye_points,
    )
    session["pairings_draft"] = pairings_to_draft(pairings)
    session.pop("current_pairings", None)
    session.modified = True
    return redirect(url_for("manual_pairings_view"))


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
                session.get("ranked_pairing_mode", RANKED_MODE_AFTER_THREE),
            )
        except SchedulingError as e:
            return render_template(
                "setup.html",
                errors=[str(e)],
                num_courts=session["num_courts"],
                game_to=game_to,
                competition_mode=competition_mode,
                ranked_pairing_mode=session.get(
                    "ranked_pairing_mode", RANKED_MODE_AFTER_THREE
                ),
                players="\n".join(session["players_scores"].keys()),
            )
        finalize_auto_pairings(pairings)

    snapshot = build_session_snapshot()
    return render_template(
        "round.html",
        pairings=session["current_pairings"],
        game_to=game_to,
        bye_points=bye_points,
        competition_mode=competition_mode,
        session_snapshot=snapshot,
    )


@app.route("/round/swap", methods=["POST"])
def swap_sit_out():
    if "current_pairings" not in session:
        return redirect(url_for("index"))

    game_to, bye_points = session_scoring()
    competition_mode = session.get("competition_mode", COMPETITION_DOUBLES)
    pairings = session["current_pairings"]
    match_kind = request.form.get("match_kind", "")
    try:
        match_index = int(request.form.get("match_index", -1))
    except ValueError:
        match_index = -1
    player_out = (request.form.get("player_out") or "").strip()

    try:
        updated = apply_sit_out_swap(
            pairings,
            match_kind,
            match_index,
            player_out,
            session["players_scores"],
            session["games_played"],
            session["sit_out_history"],
            bye_points,
        )
        updated["standings"] = standings_rows(
            session["players_scores"], session["games_played"]
        )
        session["current_pairings"] = updated
        session.modified = True
    except SchedulingError as e:
        snapshot = build_session_snapshot()
        return render_template(
            "round.html",
            pairings=pairings,
            errors=[str(e)],
            game_to=game_to,
            bye_points=bye_points,
            competition_mode=competition_mode,
            session_snapshot=snapshot,
        )

    return redirect(url_for("round_view"))


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

    def parse_match_scores(raw_a, raw_b, label):
        score_a = parse_score_value(raw_a)
        score_b = parse_score_value(raw_b)
        if score_a is None:
            errors.append(f"{label}: enter a whole number for the first score.")
        elif not 0 <= score_a <= game_to:
            errors.append(f"{label}: first score must be between 0 and {game_to}.")
        if score_b is None:
            errors.append(f"{label}: enter a whole number for the second score.")
        elif not 0 <= score_b <= game_to:
            errors.append(f"{label}: second score must be between 0 and {game_to}.")
        if score_a is None or score_b is None:
            return None
        if not (0 <= score_a <= game_to and 0 <= score_b <= game_to):
            return None
        match_err = validate_match_score(score_a, score_b, game_to)
        if match_err:
            errors.append(f"{label}: {match_err}")
            return None
        return score_a, score_b

    for i, match in enumerate(pairings["doubles"]):
        court = i + 1
        parsed = parse_match_scores(
            request.form.get(f"doubles_{i}_a", ""),
            request.form.get(f"doubles_{i}_b", ""),
            f"Court {court}",
        )
        if parsed:
            doubles_scores.append(parsed)

    for i, match in enumerate(pairings.get("singles_matches", [])):
        court = len(pairings["doubles"]) + i + 1
        p1, p2 = match
        parsed = parse_match_scores(
            request.form.get(f"singles_{i}_p1", ""),
            request.form.get(f"singles_{i}_p2", ""),
            f"Court {court} ({p1} vs {p2})",
        )
        if parsed:
            singles_scores.append(parsed)

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
            submitted_scores=dict(request.form),
        )

    record_round_history(
        pairings,
        session["singles_history"],
        session["partner_history"],
        session["matchup_history"],
        session["singles_matchup_history"],
    )
    apply_bye_points(session["players_scores"], pairings.get("byes", []), bye_points)
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
    ranked_mode = session.get("ranked_pairing_mode", RANKED_MODE_AFTER_THREE)
    next_round_num = session.get("round_num", 1) + 1
    next_uses_ranked = should_use_ranked_pairing(next_round_num, ranked_mode)
    return render_template(
        "between_rounds.html",
        round_num=session["round_num"],
        standings=standings_rows(session["players_scores"], session["games_played"]),
        session_snapshot=snapshot,
        next_uses_ranked=next_uses_ranked,
        ranked_pairing_mode=(
            RANKED_MODE_ALWAYS if next_uses_ranked else RANKED_MODE_NEVER
        ),
    )


@app.route("/round/next", methods=["POST"])
def next_round():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    if "ranked_pairing_mode" in request.form:
        session["ranked_pairing_mode"] = normalize_ranked_pairing_mode(
            request.form.get("ranked_pairing_mode")
        )
    session["round_num"] = session.get("round_num", 1) + 1
    session.pop("pairings_draft", None)
    session.modified = True
    return redirect(url_for("round_view"))


@app.route("/round/next/manual", methods=["POST"])
def next_round_manual():
    if "players_scores" not in session:
        return redirect(url_for("index"))
    if "ranked_pairing_mode" in request.form:
        session["ranked_pairing_mode"] = normalize_ranked_pairing_mode(
            request.form.get("ranked_pairing_mode")
        )
    session["round_num"] = session.get("round_num", 1) + 1
    session.pop("pairings_draft", None)
    session.pop("current_pairings", None)
    session.modified = True
    return redirect(url_for("manual_pairings_view"))


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
