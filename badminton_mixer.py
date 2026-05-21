import random

from mixer_core import (
    apply_bye_points,
    apply_round_scores,
    generate_round,
    sorted_standings,
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

    players_scores = {name: 0 for name in player_list}
    sit_out_history = {name: 0 for name in player_list}

    return num_courts, players_scores, sit_out_history


def display_round(pairings, players_scores):
    round_num = pairings["round_num"]
    print(f"\n======================================")
    print(f"      GENERATING PAIRINGS: ROUND {round_num}")
    print(f"======================================")
    if round_num > 1:
        rankings = pairings["rankings"]
        print("Current Rankings:", ", ".join([f"{k}({v}pts)" for k, v in rankings]))

    court_idx = 1
    for side_a, side_b in pairings["doubles"]:
        print(
            f"Court {court_idx} (Doubles): "
            f"({side_a[0]} & {side_a[1]}) vs ({side_b[0]} & {side_b[1]})"
        )
        court_idx += 1

    if pairings["singles"]:
        p1, p2 = pairings["singles"]
        print(f"Court {court_idx} (Singles): {p1} vs {p2}")

    if pairings["byes"]:
        names = ", ".join(pairings["byes"])
        print(f"\nSitting Out: {names} (Awarded 6 automatic points each)")
        apply_bye_points(players_scores, pairings["byes"])

    print()


def get_valid_score(prompt):
    while True:
        try:
            score = int(input(prompt))
            if 0 <= score <= 11:
                return score
            print("Scores for this format must be between 0 and 11 points.")
        except ValueError:
            print("Invalid input. Please enter a whole number.")


def enter_scores(pairings, players_scores):
    print("--- Enter final match points (0 to 11) ---")
    doubles_scores = []
    for idx, (side_a, side_b) in enumerate(pairings["doubles"], 1):
        print(f"\nCourt {idx} (Doubles):")
        score_a = get_valid_score(f"  Points for ({side_a[0]} & {side_a[1]}): ")
        score_b = get_valid_score(f"  Points for ({side_b[0]} & {side_b[1]}): ")
        doubles_scores.append((score_a, score_b))

    singles_score = None
    if pairings["singles"]:
        p1, p2 = pairings["singles"]
        court_num = len(pairings["doubles"]) + 1
        print(f"\nCourt {court_num} (Singles):")
        score_p1 = get_valid_score(f"  Points for {p1}: ")
        score_p2 = get_valid_score(f"  Points for {p2}: ")
        singles_score = (score_p1, score_p2)

    apply_round_scores(
        players_scores,
        pairings["doubles"],
        pairings["singles"],
        doubles_scores,
        singles_score,
    )


def main():
    num_courts, players_scores, sit_out_history = setup_session()
    round_num = 1

    while True:
        pairings = generate_round(num_courts, players_scores, sit_out_history, round_num)
        display_round(pairings, players_scores)
        enter_scores(pairings, players_scores)

        cont = input("\nGenerate next round? (y/n): ").strip().lower()
        if cont != "y":
            print("\n======================================")
            print("        FINAL SESSION STANDINGS       ")
            print("======================================")
            for rank, (player, score) in enumerate(sorted_standings(players_scores), 1):
                print(f"{rank:2d}. {player:<15} : {score} total points")
            print("\nThanks for organizing. See you next time!")
            break
        round_num += 1


if __name__ == "__main__":
    main()
