import random

MAX_SINGLES_GAMES = 2


def select_sitters(ranked_names, sit_out_history, players_scores, count):
    sitters = []
    pool = ranked_names.copy()
    for _ in range(count):
        min_sits = min(sit_out_history[p] for p in pool)
        eligible = [p for p in pool if sit_out_history[p] == min_sits]
        sitter = sorted(eligible, key=lambda x: players_scores[x])[0]
        sitters.append(sitter)
        sit_out_history[sitter] += 1
        pool.remove(sitter)
    return sitters


def select_singles_players(pool, singles_history, players_scores, count=2):
    """Pick singles players: max MAX_SINGLES_GAMES each, favor lower scorers."""
    pool = pool.copy()
    selected = []
    for _ in range(count):
        under_cap = [p for p in pool if singles_history.get(p, 0) < MAX_SINGLES_GAMES]
        if not under_cap:
            return None
        pick = sorted(under_cap, key=lambda p: (singles_history.get(p, 0), players_scores[p]))[0]
        selected.append(pick)
        singles_history[pick] = singles_history.get(pick, 0) + 1
        pool.remove(pick)
    return tuple(selected)


def sit_out_players(players, sit_out_history):
    for player in players:
        sit_out_history[player] += 1


def generate_round(num_courts, players_scores, sit_out_history, singles_history, round_num):
    sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    ranked_names = [p[0] for p in sorted_players]
    doubles_capacity = num_courts * 4
    sitting_out = []

    active = ranked_names.copy()
    if len(active) > doubles_capacity:
        sitting_out.extend(
            select_sitters(active, sit_out_history, players_scores, len(active) - doubles_capacity)
        )
        active = [p for p in active if p not in sitting_out]

    leftover = active[(len(active) // 4) * 4 :]

    singles = None
    if len(leftover) == 1:
        sitting_out.append(leftover[0])
        sit_out_history[leftover[0]] += 1
    elif len(leftover) in (2, 3):
        pair = select_singles_players(leftover, singles_history, players_scores)
        if not pair:
            pair = select_singles_players(active, singles_history, players_scores)
        if pair:
            singles = pair
            sitters = [p for p in leftover if p not in pair]
            sitting_out.extend(sitters)
            sit_out_players(sitters, sit_out_history)
        else:
            sitting_out.extend(leftover)
            sit_out_players(leftover, sit_out_history)

    still_playing = [
        p for p in ranked_names
        if p in active and p not in sitting_out and (not singles or p not in singles)
    ]
    doubles_player_count = (len(still_playing) // 4) * 4
    doubles_pool = still_playing[:doubles_player_count]

    if round_num == 1:
        random.shuffle(doubles_pool)

    doubles_matches = []
    for i in range(0, doubles_player_count, 4):
        tier = doubles_pool[i : i + 4]
        if round_num == 1:
            random.shuffle(tier)
        doubles_matches.append(((tier[0], tier[1]), (tier[2], tier[3])))

    return {
        "doubles": doubles_matches,
        "singles": singles,
        "byes": sitting_out,
        "rankings": sorted_players,
        "round_num": round_num,
    }


def apply_bye_points(players_scores, byes, points=6):
    for player in byes:
        players_scores[player] += points


def apply_round_scores(players_scores, doubles, singles, doubles_scores, singles_score):
    for (side_a, side_b), (score_a, score_b) in zip(doubles, doubles_scores):
        for player in side_a:
            players_scores[player] += score_a
        for player in side_b:
            players_scores[player] += score_b
    if singles and singles_score:
        p1, p2 = singles
        score_p1, score_p2 = singles_score
        players_scores[p1] += score_p1
        players_scores[p2] += score_p2


def sorted_standings(players_scores):
    return sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
