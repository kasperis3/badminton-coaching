MAX_SINGLES_GAMES = 2
MAX_SIT_OUTS = 1


class SchedulingError(Exception):
    """Raised when players/courts cannot be scheduled with at most one sit-out."""


def partner_key(side):
    return "|".join(sorted(side))


def matchup_key(side_a, side_b):
    a, b = partner_key(side_a), partner_key(side_b)
    return f"{a}::{b}" if a < b else f"{b}::{a}"


def singles_key(p1, p2):
    return "|".join(sorted([p1, p2]))


def min_courts_required(num_players):
    """
    Minimum courts so (num_players - 1) can play with exactly one sit-out.
    Playing count uses doubles (4 per court) plus optional singles (2, one court).
    """
    if num_players < 2:
        return None
    playing = num_players - 1
    remainder = playing % 4
    if remainder in (1, 3):
        return None
    doubles_courts = playing // 4
    singles_court = 1 if remainder == 2 else 0
    return doubles_courts + singles_court


def validate_session(num_players, num_courts):
    """Return an error message, or None if valid."""
    needed = min_courts_required(num_players)
    if needed is None:
        return (
            f"{num_players} players cannot be scheduled with only 1 sit-out per round "
            f"(try adding or removing 1 player)."
        )
    if num_courts < needed:
        return (
            f"Need at least {needed} court{'s' if needed != 1 else ''} for "
            f"{num_players} players with only 1 person sitting out each round "
            f"(you entered {num_courts})."
        )
    return None


def select_sitters(pool, sit_out_history, players_scores, count):
    pool = pool.copy()
    selected = []
    for _ in range(count):
        under_cap = [p for p in pool if sit_out_history.get(p, 0) < MAX_SIT_OUTS]
        if not under_cap:
            break
        pick = sorted(under_cap, key=lambda p: (sit_out_history.get(p, 0), players_scores[p]))[0]
        selected.append(pick)
        sit_out_history[pick] = sit_out_history.get(pick, 0) + 1
        pool.remove(pick)
    return selected


def pick_round_sitter(ranked_names, sit_out_history, players_scores):
    """Exactly one sit-out per round; prefer players who have sat fewer times."""
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


def best_singles_pair(pool, singles_history, singles_matchup_history, players_scores):
    under_cap = [p for p in pool if singles_history.get(p, 0) < MAX_SINGLES_GAMES]
    best = None
    best_sort = None
    for i, p1 in enumerate(under_cap):
        for p2 in under_cap[i + 1 :]:
            key = singles_key(p1, p2)
            sort_key = (
                singles_matchup_history.get(key, 0),
                singles_history.get(p1, 0) + singles_history.get(p2, 0),
                players_scores[p1] + players_scores[p2],
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


def assert_schedule_valid(sitting_out, singles, doubles_matches, all_players):
    if len(sitting_out) != 1:
        raise SchedulingError(
            f"Internal error: expected 1 sit-out, got {len(sitting_out)} ({sitting_out})."
        )

    assigned = {}
    for player in sitting_out:
        assigned[player] = assigned.get(player, 0) + 1

    if singles:
        for player in singles:
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


def generate_round(
    num_courts,
    players_scores,
    sit_out_history,
    singles_history,
    partner_history,
    matchup_history,
    singles_matchup_history,
    round_num,
):
    ranked_names = [
        p for p, _ in sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    ]
    num_players = len(ranked_names)

    err = validate_session(num_players, num_courts)
    if err:
        raise SchedulingError(err)

    sitting_out = []
    assign_round_sitter(ranked_names, sitting_out, sit_out_history, players_scores)

    queue = [p for p in ranked_names if p not in sitting_out]
    singles = None

    if len(queue) % 4 == 2:
        pair = best_singles_pair(
            queue, singles_history, singles_matchup_history, players_scores
        )
        if not pair:
            raise SchedulingError("Cannot form a singles match for this round.")
        record_singles_pair(pair, singles_history, singles_matchup_history)
        singles = pair
        queue = [p for p in queue if p not in singles]

    max_doubles_courts = num_courts - (1 if singles else 0)
    doubles_matches = []
    while len(queue) >= 4 and len(doubles_matches) < max_doubles_courts:
        tier = queue[:4]
        queue = queue[4:]
        side_a, side_b = best_doubles_split(tier, partner_history, matchup_history)
        record_doubles_match(side_a, side_b, partner_history, matchup_history)
        doubles_matches.append((side_a, side_b))

    if queue:
        raise SchedulingError("Internal error: unassigned players remain after scheduling.")

    assert_schedule_valid(sitting_out, singles, doubles_matches, ranked_names)

    sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    return {
        "doubles": doubles_matches,
        "singles": singles,
        "byes": sitting_out,
        "rankings": sorted_players,
        "round_num": round_num,
    }


def record_games_played(games_played, doubles_matches, singles):
    seen = set()
    for side_a, side_b in doubles_matches:
        for player in side_a + side_b:
            if player in seen:
                raise SchedulingError(f"{player} counted twice in games played.")
            seen.add(player)
            games_played[player] = games_played.get(player, 0) + 1
    if singles:
        for player in singles:
            if player in seen:
                raise SchedulingError(f"{player} counted twice in games played.")
            seen.add(player)
            games_played[player] = games_played.get(player, 0) + 1


def apply_bye_points(players_scores, byes, points=6):
    for player in byes:
        players_scores[player] += points


def standings_rows(players_scores, games_played):
    return [
        (name, score, games_played.get(name, 0))
        for name, score in sorted_standings(players_scores)
    ]


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
