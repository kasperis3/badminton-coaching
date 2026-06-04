import random

MAX_SINGLES_GAMES = 2
MAX_SIT_OUTS = 1
ALLOWED_GAME_TO = (7, 11, 15, 21)
DEFAULT_GAME_TO = 7
RANKED_PAIRING_START_ROUND = 4
COMPETITION_DOUBLES = "doubles"
COMPETITION_SINGLES = "singles"


class SchedulingError(Exception):
    """Raised when players/courts cannot be scheduled with at most one sit-out."""


def partner_key(side):
    return "|".join(sorted(side))


def matchup_key(side_a, side_b):
    a, b = partner_key(side_a), partner_key(side_b)
    return f"{a}::{b}" if a < b else f"{b}::{a}"


def singles_key(p1, p2):
    return "|".join(sorted([p1, p2]))


def normalize_competition_mode(value):
    if value == COMPETITION_SINGLES:
        return COMPETITION_SINGLES
    return COMPETITION_DOUBLES


def min_courts_for_playing_doubles(playing_count):
    if playing_count < 2:
        return None
    remainder = playing_count % 4
    if remainder in (1, 3):
        return None
    return playing_count // 4 + (1 if remainder == 2 else 0)


def resolve_sit_outs_doubles(num_players):
    if min_courts_for_playing_doubles(num_players) is not None:
        return 0
    if min_courts_for_playing_doubles(num_players - 1) is not None:
        return 1
    return None


def resolve_sit_outs_singles(num_players):
    if num_players < 2:
        return None
    return 0 if num_players % 2 == 0 else 1


def min_courts_singles(num_players, sit_outs):
    playing = num_players - sit_outs
    if playing < 2:
        return None
    return playing // 2


def validate_session(num_players, num_courts, competition_mode=COMPETITION_DOUBLES):
    if num_players < 2:
        return None
    mode = normalize_competition_mode(competition_mode)
    if mode == COMPETITION_SINGLES:
        sit_outs = resolve_sit_outs_singles(num_players)
        if sit_outs is None:
            return f"{num_players} players cannot be scheduled."
        needed = min_courts_singles(num_players, sit_outs)
        if num_courts < needed:
            sit_note = "everyone plays" if sit_outs == 0 else "1 sit-out per round"
            return (
                f"Need at least {needed} court{'s' if needed != 1 else ''} for "
                f"{num_players} players in singles mode ({sit_note}; you entered {num_courts})."
            )
        return None
    sit_outs = resolve_sit_outs_doubles(num_players)
    if sit_outs is None:
        return (
            f"{num_players} players cannot be scheduled "
            f"(try adding or removing 1 player)."
        )
    needed = min_courts_for_playing_doubles(num_players - sit_outs)
    if num_courts < needed:
        sit_note = "everyone plays" if sit_outs == 0 else "1 sit-out per round"
        return (
            f"Need at least {needed} court{'s' if needed != 1 else ''} for "
            f"{num_players} players ({sit_note}; you entered {num_courts})."
        )
    return None


def bye_points_for_game_to(game_to):
    return game_to // 2 + 1


def normalize_game_to(value):
    try:
        game_to = int(value)
    except (TypeError, ValueError):
        return DEFAULT_GAME_TO
    return game_to if game_to in ALLOWED_GAME_TO else DEFAULT_GAME_TO


def ranked_by_score(players, players_scores):
    return sorted(players, key=lambda p: players_scores[p], reverse=True)


def order_active_players(active, players_scores, use_ranked):
    if use_ranked:
        return ranked_by_score(active, players_scores)
    queue = active.copy()
    random.shuffle(queue)
    return queue


def pick_round_sitter(ranked_names, sit_out_history, players_scores):
    under_cap = [p for p in ranked_names if sit_out_history.get(p, 0) < MAX_SIT_OUTS]
    pool = under_cap if under_cap else ranked_names
    return sorted(pool, key=lambda p: (sit_out_history.get(p, 0), players_scores[p]))[0]


def assign_round_sitter(ranked_names, sitting_out, sit_out_history, players_scores):
    sitter = pick_round_sitter(ranked_names, sit_out_history, players_scores)
    if sit_out_history.get(sitter, 0) < MAX_SIT_OUTS:
        sitting_out.append(sitter)
        sit_out_history[sitter] = sit_out_history.get(sitter, 0) + 1
    else:
        sitting_out.append(sitter)
    return sitter


def best_singles_pair(pool, singles_history, singles_matchup_history, players_scores, use_ranked):
    under_cap = [p for p in pool if singles_history.get(p, 0) < MAX_SINGLES_GAMES]
    best = None
    best_sort = None
    for i, p1 in enumerate(under_cap):
        for p2 in under_cap[i + 1 :]:
            key = singles_key(p1, p2)
            if use_ranked:
                sort_key = (
                    singles_matchup_history.get(key, 0),
                    singles_history.get(p1, 0) + singles_history.get(p2, 0),
                    players_scores[p1] + players_scores[p2],
                )
            else:
                sort_key = (
                    singles_matchup_history.get(key, 0),
                    singles_history.get(p1, 0) + singles_history.get(p2, 0),
                )
            if best_sort is None or sort_key < best_sort:
                best = (p1, p2)
                best_sort = sort_key
    return best


def record_singles_pair(pair, singles_history, singles_matchup_history):
    p1, p2 = pair
    singles_history[p1] = singles_history.get(p1, 0) + 1
    singles_history[p2] = singles_history.get(p2, 0) + 1
    key = singles_key(p1, p2)
    singles_matchup_history[key] = singles_matchup_history.get(key, 0) + 1


def best_doubles_split(tier, partner_history, matchup_history):
    a, b, c, d = tier
    splits = [
        ((a, b), (c, d)),
        ((a, c), (b, d)),
        ((a, d), (b, c)),
    ]
    best = None
    best_sort = None
    for side_a, side_b in splits:
        cost = (
            partner_history.get(partner_key(side_a), 0)
            + partner_history.get(partner_key(side_b), 0)
            + matchup_history.get(matchup_key(side_a, side_b), 0) * 2
        )
        strength_penalty = 0 if side_a == (a, b) else 1
        sort_key = (cost, strength_penalty)
        if best_sort is None or sort_key < best_sort:
            best = (side_a, side_b)
            best_sort = sort_key
    return best


def record_doubles_match(side_a, side_b, partner_history, matchup_history):
    partner_history[partner_key(side_a)] = partner_history.get(partner_key(side_a), 0) + 1
    partner_history[partner_key(side_b)] = partner_history.get(partner_key(side_b), 0) + 1
    mkey = matchup_key(side_a, side_b)
    matchup_history[mkey] = matchup_history.get(mkey, 0) + 1


def assert_schedule_valid(sitting_out, singles_matches, doubles_matches, all_players):
    if len(sitting_out) not in (0, 1):
        raise SchedulingError(
            f"Internal error: expected 0 or 1 sit-out, got {len(sitting_out)} ({sitting_out})."
        )

    assigned = {}
    for player in sitting_out:
        assigned[player] = assigned.get(player, 0) + 1

    for match in singles_matches:
        for player in match:
            assigned[player] = assigned.get(player, 0) + 1

    for side_a, side_b in doubles_matches:
        for player in side_a + side_b:
            assigned[player] = assigned.get(player, 0) + 1

    for player in all_players:
        count = assigned.get(player, 0)
        if count == 0:
            raise SchedulingError(f"Internal error: {player} was not scheduled.")
        if count > 1:
            raise SchedulingError(
                f"Internal error: {player} was scheduled for {count} games this round."
            )


def _round_result(
    doubles_matches, singles_matches, sitting_out, ranked_names, players_scores, round_num
):
    sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    use_ranked = round_num >= RANKED_PAIRING_START_ROUND
    return {
        "doubles": doubles_matches,
        "singles_matches": singles_matches,
        "byes": sitting_out,
        "rankings": sorted_players,
        "round_num": round_num,
        "use_ranked_pairing": use_ranked,
    }


def generate_round_doubles(
    num_courts,
    players_scores,
    sit_out_history,
    singles_history,
    partner_history,
    matchup_history,
    singles_matchup_history,
    round_num,
):
    ranked_names = ranked_by_score(players_scores.keys(), players_scores)
    num_players = len(ranked_names)
    use_ranked = round_num >= RANKED_PAIRING_START_ROUND

    sit_out_count = resolve_sit_outs_doubles(num_players)
    sitting_out = []
    if sit_out_count == 1:
        assign_round_sitter(ranked_names, sitting_out, sit_out_history, players_scores)

    active = [p for p in ranked_names if p not in sitting_out]
    queue = order_active_players(active, players_scores, use_ranked)
    singles_matches = []

    if len(queue) % 4 == 2:
        pair = best_singles_pair(
            queue, singles_history, singles_matchup_history, players_scores, use_ranked
        )
        if not pair:
            raise SchedulingError("Cannot form a singles match for this round.")
        record_singles_pair(pair, singles_history, singles_matchup_history)
        singles_matches.append(pair)
        queue = [p for p in queue if p not in pair]

    max_doubles_courts = num_courts - len(singles_matches)
    doubles_matches = []
    while len(queue) >= 4 and len(doubles_matches) < max_doubles_courts:
        tier = queue[:4]
        queue = queue[4:]
        side_a, side_b = best_doubles_split(tier, partner_history, matchup_history)
        record_doubles_match(side_a, side_b, partner_history, matchup_history)
        doubles_matches.append((side_a, side_b))

    if queue:
        raise SchedulingError("Internal error: unassigned players remain after scheduling.")

    assert_schedule_valid(sitting_out, singles_matches, doubles_matches, ranked_names)
    return _round_result(
        doubles_matches, singles_matches, sitting_out, ranked_names, players_scores, round_num
    )


def generate_round_singles(
    num_courts,
    players_scores,
    sit_out_history,
    singles_history,
    partner_history,
    matchup_history,
    singles_matchup_history,
    round_num,
):
    ranked_names = ranked_by_score(players_scores.keys(), players_scores)
    num_players = len(ranked_names)
    use_ranked = round_num >= RANKED_PAIRING_START_ROUND

    sitting_out = []
    if resolve_sit_outs_singles(num_players) == 1:
        assign_round_sitter(ranked_names, sitting_out, sit_out_history, players_scores)

    active = [p for p in ranked_names if p not in sitting_out]
    remaining = order_active_players(active, players_scores, use_ranked)
    singles_matches = []

    while len(singles_matches) < num_courts and len(remaining) >= 2:
        pair = best_singles_pair(
            remaining, singles_history, singles_matchup_history, players_scores, use_ranked
        )
        if not pair:
            break
        record_singles_pair(pair, singles_history, singles_matchup_history)
        singles_matches.append(pair)
        remaining = [p for p in remaining if p not in pair]

    if remaining:
        raise SchedulingError(
            "Internal error: unassigned players remain after singles scheduling."
        )

    assert_schedule_valid(sitting_out, singles_matches, [], ranked_names)
    return _round_result([], singles_matches, sitting_out, ranked_names, players_scores, round_num)


def generate_round(
    num_courts,
    players_scores,
    sit_out_history,
    singles_history,
    partner_history,
    matchup_history,
    singles_matchup_history,
    round_num,
    competition_mode=COMPETITION_DOUBLES,
):
    num_players = len(players_scores)
    mode = normalize_competition_mode(competition_mode)
    err = validate_session(num_players, num_courts, mode)
    if err:
        raise SchedulingError(err)

    if mode == COMPETITION_SINGLES:
        return generate_round_singles(
            num_courts,
            players_scores,
            sit_out_history,
            singles_history,
            partner_history,
            matchup_history,
            singles_matchup_history,
            round_num,
        )
    return generate_round_doubles(
        num_courts,
        players_scores,
        sit_out_history,
        singles_history,
        partner_history,
        matchup_history,
        singles_matchup_history,
        round_num,
    )


def record_games_played(games_played, doubles_matches, singles_matches):
    seen = set()
    for side_a, side_b in doubles_matches:
        for player in side_a + side_b:
            if player in seen:
                raise SchedulingError(f"{player} counted twice in games played.")
            seen.add(player)
            games_played[player] = games_played.get(player, 0) + 1
    for match in singles_matches:
        for player in match:
            if player in seen:
                raise SchedulingError(f"{player} counted twice in games played.")
            seen.add(player)
            games_played[player] = games_played.get(player, 0) + 1


def apply_bye_points(players_scores, byes, points):
    for player in byes:
        players_scores[player] += points


def standings_rows(players_scores, games_played):
    return [
        (name, score, games_played.get(name, 0))
        for name, score in sorted_standings(players_scores)
    ]


def apply_round_scores(players_scores, doubles, singles_matches, doubles_scores, singles_scores):
    for (side_a, side_b), (score_a, score_b) in zip(doubles, doubles_scores):
        for player in side_a:
            players_scores[player] += score_a
        for player in side_b:
            players_scores[player] += score_b
    for (p1, p2), (score_p1, score_p2) in zip(singles_matches, singles_scores):
        players_scores[p1] += score_p1
        players_scores[p2] += score_p2


def sorted_standings(players_scores):
    return sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
