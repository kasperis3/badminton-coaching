from mixer_core import (
    ALLOWED_GAME_TO,
    COMPETITION_DOUBLES,
    COMPETITION_SINGLES,
    DEFAULT_GAME_TO,
    RANKED_PAIRING_START_ROUND,
    SchedulingError,
    apply_bye_points,
    apply_round_scores,
    bye_points_for_game_to,
    generate_round,
    normalize_competition_mode,
    normalize_game_to,
    record_games_played,
    standings_rows,
    validate_match_score,
)


def setup_session():
    print("======================================")
    print("     BADMINTON SESSION SETUP          ")
    print("======================================")

    while True:
        try:
            num_courts = int(input("Enter the number of courts available: "))
            if num_courts > 0:
                break
            print("Please enter a number greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    while True:
        mode_raw = input("Competition (doubles/singles) [doubles]: ").strip().lower()
        competition_mode = normalize_competition_mode(
            COMPETITION_SINGLES if mode_raw.startswith("s") else COMPETITION_DOUBLES
        )
        break

    while True:
        raw = input(f"Game to (7/11/15/21) [{DEFAULT_GAME_TO}]: ").strip()
        game_to = normalize_game_to(raw or DEFAULT_GAME_TO)
        if not raw or game_to in ALLOWED_GAME_TO:
            break
        print(f"  Choose one of: {', '.join(map(str, ALLOWED_GAME_TO))}")

    print("\nEnter player names one by one (Press Enter on an empty line when done):")
    player_list = []
    while True:
        name = input(f"  Player {len(player_list) + 1} name: ").strip()
        if not name:
            if len(player_list) < 2:
                print("  You need at least 2 players to play!")
                continue
            break
        if name in player_list:
            print("  That name already exists. Please use a unique name or add an initial.")
            continue
        player_list.append(name)

    while True:
        err = validate_session(len(player_list), num_courts, competition_mode)
        if not err:
            break
        print(f"\n  {err}")
        try:
            num_courts = int(input("Enter the number of courts available: "))
        except ValueError:
            print("Invalid input. Please enter a number.")

    players_scores = {name: 0 for name in player_list}
    games_played = {name: 0 for name in player_list}
    sit_out_history = {name: 0 for name in player_list}
    singles_history = {name: 0 for name in player_list}
    partner_history = {}
    matchup_history = {}
    singles_matchup_history = {}

    return (
        num_courts,
        game_to,
        competition_mode,
        players_scores,
        games_played,
        sit_out_history,
        singles_history,
        partner_history,
        matchup_history,
        singles_matchup_history,
    )


def display_round(pairings, players_scores, games_played, game_to, bye_points, competition_mode):
    round_num = pairings["round_num"]
    mode_label = "Singles" if competition_mode == COMPETITION_SINGLES else "Doubles"
    phase = (
        "ranked"
        if pairings.get("use_ranked_pairing")
        else f"random (rounds 1–{RANKED_PAIRING_START_ROUND - 1})"
    )
    print(f"\n======================================")
    print(f"      GENERATING PAIRINGS: ROUND {round_num} ({mode_label}, {phase})")
    print(f"======================================")
    if round_num > 1:
        for rank, (name, score, games) in enumerate(
            standings_rows(players_scores, games_played), 1
        ):
            print(f"  {rank:2d}. {name:<12} {score:3d} pts  {games} GP")

    court_idx = 1
    for side_a, side_b in pairings["doubles"]:
        print(
            f"Court {court_idx} (Doubles): "
            f"({side_a[0]} & {side_a[1]}) vs ({side_b[0]} & {side_b[1]})"
        )
        court_idx += 1

    for match in pairings["singles_matches"]:
        print(f"Court {court_idx} (Singles): {match[0]} vs {match[1]}")
        court_idx += 1

    if pairings["byes"]:
        names = ", ".join(pairings["byes"])
        print(f"\nSitting Out: {names} (Awarded {bye_points} automatic points each)")

    print()


def get_valid_score(prompt, game_to):
    while True:
        try:
            score = int(input(prompt))
            if 0 <= score <= game_to:
                return score
            print(f"Scores for this format must be between 0 and {game_to} points.")
        except ValueError:
            print("Invalid input. Please enter a whole number.")


def get_valid_match_scores(side_a_label, side_b_label, game_to):
    while True:
        score_a = get_valid_score(side_a_label, game_to)
        score_b = get_valid_score(side_b_label, game_to)
        match_err = validate_match_score(score_a, score_b, game_to)
        if match_err:
            print(f"  {match_err} Try again.")
            continue
        return score_a, score_b


def enter_scores(pairings, players_scores, game_to):
    print(f"--- Enter final match points (0 to {game_to}; one side must reach {game_to}) ---")
    doubles_scores = []
    for idx, (side_a, side_b) in enumerate(pairings["doubles"], 1):
        print(f"\nCourt {idx} (Doubles):")
        score_a, score_b = get_valid_match_scores(
            f"  Points for ({side_a[0]} & {side_a[1]}): ",
            f"  Points for ({side_b[0]} & {side_b[1]}): ",
            game_to,
        )
        doubles_scores.append((score_a, score_b))

    singles_scores = []
    for idx, (p1, p2) in enumerate(pairings["singles_matches"], len(pairings["doubles"]) + 1):
        print(f"\nCourt {idx} (Singles):")
        score_p1, score_p2 = get_valid_match_scores(
            f"  Points for {p1}: ",
            f"  Points for {p2}: ",
            game_to,
        )
        singles_scores.append((score_p1, score_p2))

    apply_round_scores(
        players_scores,
        pairings["doubles"],
        pairings["singles_matches"],
        doubles_scores,
        singles_scores,
    )


def main():
    (
        num_courts,
        game_to,
        competition_mode,
        players_scores,
        games_played,
        sit_out_history,
        singles_history,
        partner_history,
        matchup_history,
        singles_matchup_history,
    ) = setup_session()
    bye_points = bye_points_for_game_to(game_to)
    round_num = 1

    while True:
        try:
            pairings = generate_round(
                num_courts,
                players_scores,
                sit_out_history,
                singles_history,
                partner_history,
                matchup_history,
                singles_matchup_history,
                round_num,
                competition_mode,
            )
        except SchedulingError as e:
            print(f"\nScheduling error: {e}")
            break
        apply_bye_points(players_scores, pairings["byes"], bye_points)
        record_games_played(
            games_played, pairings["doubles"], pairings["singles_matches"]
        )
        display_round(
            pairings, players_scores, games_played, game_to, bye_points, competition_mode
        )
        enter_scores(pairings, players_scores, game_to)

        cont = input("\nGenerate next round? (y/n): ").strip().lower()
        if cont != "y":
            print("\n======================================")
            print("        FINAL SESSION STANDINGS       ")
            print("======================================")
            for rank, (player, score, games) in enumerate(
                standings_rows(players_scores, games_played), 1
            ):
                print(f"{rank:2d}. {player:<15} : {score} pts  ({games} games)")
            print("\nThanks for organizing. See you next time!")
            break
        round_num += 1


if __name__ == "__main__":
    main()
