MAX_SINGLES_GAMES = 2
MAX_SIT_OUTS = 1


def partner_key(side):
    """JSON-safe session key for a doubles pair."""
    return "|".join(sorted(side))


def matchup_key(side_a, side_b):
    """JSON-safe session key for a doubles team vs team."""
    a, b = partner_key(side_a), partner_key(side_b)
    return f"{a}::{b}" if a < b else f"{b}::{a}"


def singles_key(p1, p2):
    """JSON-safe session key for a singles matchup."""
    return "|".join(sorted([p1, p2]))


def select_sitters(pool, sit_out_history, players_scores, count):
    """Pick sitters: max MAX_SIT_OUTS each. Returns as many as possible (may be fewer)."""
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


def best_singles_pair(pool, singles_history, singles_matchup_history, players_scores):
    """Pick a singles pair: under game cap, fewest past meetings, favor lower scorers."""
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


def select_singles_players(pool, singles_history, singles_matchup_history, players_scores):
    pair = best_singles_pair(pool, singles_history, singles_matchup_history, players_scores)
    if pair:
        record_singles_pair(pair, singles_history, singles_matchup_history)
    return pair


def form_singles_pair(anchor, pool, singles_history, singles_matchup_history, players_scores):
    """Pair anchor for singles when anchor cannot sit out again."""
    if singles_history.get(anchor, 0) >= MAX_SINGLES_GAMES:
        return None
    others = [
        p
        for p in pool
        if p != anchor and singles_history.get(p, 0) < MAX_SINGLES_GAMES
    ]
    if not others:
        return None
    best_partner = None
    best_sort = None
    for p in others:
        key = singles_key(anchor, p)
        sort_key = (
            singles_matchup_history.get(key, 0),
            singles_history.get(p, 0),
            players_scores[p],
        )
        if best_sort is None or sort_key < best_sort:
            best_partner = p
            best_sort = sort_key
    pair = (anchor, best_partner)
    record_singles_pair(pair, singles_history, singles_matchup_history)
    return pair


def try_sit_out(player, sitting_out, sit_out_history):
    if sit_out_history.get(player, 0) < MAX_SIT_OUTS:
        sitting_out.append(player)
        sit_out_history[player] = sit_out_history.get(player, 0) + 1
        return True
    return False


def show_as_sitting_out(player, sitting_out):
    """List player as sitting out without awarding bye points again."""
    if player not in sitting_out:
        sitting_out.append(player)


def best_doubles_split(tier, partner_history, matchup_history):
    """From 4 players (strongest-first), pick teams vs teams with fewest repeats."""
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


def assign_singles(pool, singles, sitting_out, active, singles_history, singles_matchup_history, players_scores):
    """Assign a singles pair from pool; return updated singles tuple or None."""
    pair = select_singles_players(pool, singles_history, singles_matchup_history, players_scores)
    if pair:
        return pair
    return singles


def schedule_remainder(
    remainder_players,
    pool,
    singles,
    sitting_out,
    active,
    sit_out_history,
    singles_history,
    singles_matchup_history,
    players_scores,
):
    """Handle 1–3 players who do not fill a full doubles court."""
    if not remainder_players:
        return singles

    if len(remainder_players) == 1:
        player = remainder_players[0]
        if try_sit_out(player, sitting_out, sit_out_history):
            return singles
        pair = form_singles_pair(
            player, pool, singles_history, singles_matchup_history, players_scores
        )
        return pair if pair else singles

    if len(remainder_players) == 2:
        pair = assign_singles(
            remainder_players,
            singles,
            sitting_out,
            active,
            singles_history,
            singles_matchup_history,
            players_scores,
        )
        return pair

    pair = assign_singles(
        remainder_players,
        singles,
        sitting_out,
        active,
        singles_history,
        singles_matchup_history,
        players_scores,
    )
    if pair:
        for player in remainder_players:
            if player not in pair:
                try_sit_out(player, sitting_out, sit_out_history)
        return pair

    for player in remainder_players:
        try_sit_out(player, sitting_out, sit_out_history)
    return singles


def ensure_all_scheduled(
    active,
    sitting_out,
    singles,
    doubles_matches,
    sit_out_history,
    singles_history,
    singles_matchup_history,
    players_scores,
    num_courts,
):
    """Ensure every active player is in doubles, singles, or sitting out (visible)."""
    scheduled = set(sitting_out)
    if singles:
        scheduled.update(singles)
    for side_a, side_b in doubles_matches:
        scheduled.update(side_a)
        scheduled.update(side_b)

    unscheduled = [p for p in active if p not in scheduled]

    for player in unscheduled:
        if try_sit_out(player, sitting_out, sit_out_history):
            scheduled.add(player)
            continue
        if singles is None:
            pair = form_singles_pair(
                player, active, singles_history, singles_matchup_history, players_scores
            )
            if pair:
                singles = pair
                scheduled.update(pair)
                continue
        elif player not in singles:
            pair = form_singles_pair(
                player, active, singles_history, singles_matchup_history, players_scores
            )
            if pair:
                singles = pair
                scheduled.update(pair)
                continue
        show_as_sitting_out(player, sitting_out)
        scheduled.add(player)

    return singles, sitting_out


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
    sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    ranked_names = [p[0] for p in sorted_players]
    doubles_capacity = num_courts * 4
    sitting_out = []
    singles = None
    doubles_matches = []

    queue = ranked_names.copy()

    if len(queue) > doubles_capacity:
        sitters = select_sitters(queue, sit_out_history, players_scores, len(queue) - doubles_capacity)
        sitting_out.extend(sitters)
        queue = [p for p in queue if p not in sitting_out]

    remainder_count = len(queue) % 4
    if remainder_count:
        remainder_players = queue[-remainder_count:]
        queue = queue[:-remainder_count]
        singles = schedule_remainder(
            remainder_players,
            ranked_names,
            singles,
            sitting_out,
            ranked_names,
            sit_out_history,
            singles_history,
            singles_matchup_history,
            players_scores,
        )

    while len(queue) >= 4 and len(doubles_matches) < num_courts:
        tier = queue[:4]
        queue = queue[4:]
        side_a, side_b = best_doubles_split(tier, partner_history, matchup_history)
        record_doubles_match(side_a, side_b, partner_history, matchup_history)
        doubles_matches.append((side_a, side_b))

    active = ranked_names
    singles, sitting_out = ensure_all_scheduled(
        active,
        sitting_out,
        singles,
        doubles_matches,
        sit_out_history,
        singles_history,
        singles_matchup_history,
        players_scores,
        num_courts,
    )

    return {
        "doubles": doubles_matches,
        "singles": singles,
        "byes": sitting_out,
        "rankings": sorted_players,
        "round_num": round_num,
    }


def record_games_played(games_played, doubles_matches, singles):
    for side_a, side_b in doubles_matches:
        for player in side_a + side_b:
            games_played[player] = games_played.get(player, 0) + 1
    if singles:
        for player in singles:
            games_played[player] = games_played.get(player, 0) + 1


def apply_bye_points(players_scores, byes, points=6):
    """All sit-outs (including forced rest) receive bye points."""
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
