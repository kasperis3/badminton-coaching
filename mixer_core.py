import random


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


def generate_round(num_courts, players_scores, sit_out_history, round_num):
    sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    ranked_names = [p[0] for p in sorted_players]
    total_players = len(ranked_names)

    max_playing = num_courts * 2
    playing_count = min(total_players, max_playing)
    if playing_count % 2 == 1:
        playing_count -= 1

    sit_out_count = total_players - playing_count
    sitting_out = (
        select_sitters(ranked_names, sit_out_history, players_scores, sit_out_count)
        if sit_out_count
        else []
    )

    playing_pool = [p for p in ranked_names if p not in sitting_out]
    if round_num == 1:
        random.shuffle(playing_pool)

    matches = []
    for i in range(0, playing_count, 2):
        matches.append((playing_pool[i], playing_pool[i + 1]))

    return {
        "matches": matches,
        "byes": sitting_out,
        "rankings": sorted_players,
        "round_num": round_num,
    }


def apply_bye_points(players_scores, byes, points=6):
    for player in byes:
        players_scores[player] += points


def apply_match_scores(players_scores, matches, scores):
    for (p1, p2), (score_p1, score_p2) in zip(matches, scores):
        players_scores[p1] += score_p1
        players_scores[p2] += score_p2


def sorted_standings(players_scores):
    return sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
