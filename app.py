import os
import socket

from flask import Flask, redirect, render_template, request, session, url_for

from mixer_core import (
    apply_bye_points,
    apply_round_scores,
    generate_round,
    sorted_standings,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baddy-dev-change-me-in-production")


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

    players = parse_players(request.form.get("players", ""))

    errors = []
    if num_courts < 1:
        errors.append("Enter at least 1 court.")
    if len(players) < 2:
        errors.append("Add at least 2 unique player names.")

    if errors:
        return render_template(
            "setup.html",
            errors=errors,
            num_courts=num_courts or "",
            players=request.form.get("players", ""),
        )

    session["num_courts"] = num_courts
    session["players_scores"] = {name: 0 for name in players}
    session["sit_out_history"] = {name: 0 for name in players}
    session["round_num"] = 1

    return redirect(url_for("round_view"))


@app.route("/round")
def round_view():
    if "players_scores" not in session:
        return redirect(url_for("index"))

    if "current_pairings" not in session:
        pairings = generate_round(
            session["num_courts"],
            session["players_scores"],
            session["sit_out_history"],
            session["round_num"],
        )
        apply_bye_points(session["players_scores"], pairings["byes"])
        session["current_pairings"] = {
            "doubles": pairings["doubles"],
            "singles": pairings["singles"],
            "byes": pairings["byes"],
            "round_num": pairings["round_num"],
            "rankings": pairings["rankings"],
        }
        session.modified = True

    return render_template("round.html", pairings=session["current_pairings"])


@app.route("/round/scores", methods=["POST"])
def submit_scores():
    if "current_pairings" not in session:
        return redirect(url_for("index"))

    pairings = session["current_pairings"]
    doubles_scores = []
    errors = []

    def parse_score(raw, label):
        try:
            score = int(raw.strip())
        except ValueError:
            errors.append(f"{label}: enter a whole number.")
            return None
        if not 0 <= score <= 11:
            errors.append(f"{label}: score must be between 0 and 11.")
            return None
        return score

    for i, match in enumerate(pairings["doubles"]):
        court = i + 1
        score_a = parse_score(request.form.get(f"doubles_{i}_a", ""), f"Court {court} team A")
        score_b = parse_score(request.form.get(f"doubles_{i}_b", ""), f"Court {court} team B")
        if score_a is None or score_b is None:
            continue
        doubles_scores.append((score_a, score_b))

    singles_score = None
    if pairings["singles"]:
        court = len(pairings["doubles"]) + 1
        p1, p2 = pairings["singles"]
        score_p1 = parse_score(request.form.get("singles_p1", ""), f"Court {court} {p1}")
        score_p2 = parse_score(request.form.get("singles_p2", ""), f"Court {court} {p2}")
        if score_p1 is not None and score_p2 is not None:
            singles_score = (score_p1, score_p2)

    expected_doubles = len(pairings["doubles"])
    singles_ok = not pairings["singles"] or singles_score is not None
    if errors or len(doubles_scores) != expected_doubles or not singles_ok:
        return render_template("round.html", pairings=pairings, errors=errors)

    apply_round_scores(
        session["players_scores"],
        pairings["doubles"],
        pairings["singles"],
        doubles_scores,
        singles_score,
    )
    session.pop("current_pairings", None)
    session.modified = True

    return render_template(
        "between_rounds.html",
        round_num=session["round_num"],
        standings=sorted_standings(session["players_scores"]),
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
    standings = sorted_standings(session["players_scores"])
    session.clear()
    return render_template("standings.html", standings=standings)


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
