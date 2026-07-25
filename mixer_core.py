import random

MAX_SINGLES_GAMES = 2
MAX_SIT_OUTS = 1
ALLOWED_GAME_TO = (7, 11, 15, 21)
DEFAULT_GAME_TO = 7
RANKED_PAIRING_START_ROUND = 4
RANKED_MODE_AFTER_THREE = "after_three"
RANKED_MODE_NEVER = "never"
RANKED_MODE_ALWAYS = "always"
COMPETITION_DOUBLES = "doubles"
COMPETITION_SINGLES = "singles"
PAIRING_AUTO = "auto"
PAIRING_MANUAL = "manual"


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


def normalize_ranked_pairing_mode(value):
    if value == RANKED_MODE_NEVER:
        return RANKED_MODE_NEVER
    if value == RANKED_MODE_ALWAYS:
        return RANKED_MODE_ALWAYS
    return RANKED_MODE_AFTER_THREE


def should_use_ranked_pairing(round_num, ranked_pairing_mode=RANKED_MODE_AFTER_THREE):
    mode = normalize_ranked_pairing_mode(ranked_pairing_mode)
    if mode == RANKED_MODE_NEVER:
        return False
    if mode == RANKED_MODE_ALWAYS:
        return True
    return round_num >= RANKED_PAIRING_START_ROUND


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
    """Pick who sits: fewest sit-outs first; among ties, lower score (bye catch-up)."""
    under_cap = [p for p in ranked_names if sit_out_history.get(p, 0) < MAX_SIT_OUTS]
    pool = under_cap if under_cap else ranked_names
    return sorted(pool, key=lambda p: (sit_out_history.get(p, 0), players_scores[p]))[0]


def assign_round_sitter(ranked_names, sitting_out, sit_out_history, players_scores):
    sitter = pick_round_sitter(ranked_names, sit_out_history, players_scores)
    sitting_out.append(sitter)
    sit_out_history[sitter] = sit_out_history.get(sitter, 0) + 1
    return sitter


def best_singles_pair(pool, singles_history, singles_matchup_history, players_scores, use_ranked):
    under_cap = [p for p in pool if singles_history.get(p, 0) < MAX_SINGLES_GAMES]
    candidates = under_cap if len(under_cap) >= 2 else pool
    if len(candidates) < 2:
        return None
    best = None
    best_sort = None
    for i, p1 in enumerate(candidates):
        for p2 in candidates[i + 1 :]:
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
    doubles_matches,
    singles_matches,
    sitting_out,
    ranked_names,
    players_scores,
    round_num,
    ranked_pairing_mode=RANKED_MODE_AFTER_THREE,
):
    sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
    use_ranked = should_use_ranked_pairing(round_num, ranked_pairing_mode)
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
    ranked_pairing_mode=RANKED_MODE_AFTER_THREE,
):
    ranked_names = ranked_by_score(players_scores.keys(), players_scores)
    num_players = len(ranked_names)
    use_ranked = should_use_ranked_pairing(round_num, ranked_pairing_mode)

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
        singles_matches.append(pair)
        queue = [p for p in queue if p not in pair]

    max_doubles_courts = num_courts - len(singles_matches)
    doubles_matches = []
    while len(queue) >= 4 and len(doubles_matches) < max_doubles_courts:
        tier = queue[:4]
        queue = queue[4:]
        side_a, side_b = best_doubles_split(tier, partner_history, matchup_history)
        doubles_matches.append((side_a, side_b))

    if queue:
        raise SchedulingError("Internal error: unassigned players remain after scheduling.")

    assert_schedule_valid(sitting_out, singles_matches, doubles_matches, ranked_names)
    return _round_result(
        doubles_matches,
        singles_matches,
        sitting_out,
        ranked_names,
        players_scores,
        round_num,
        ranked_pairing_mode,
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
    ranked_pairing_mode=RANKED_MODE_AFTER_THREE,
):
    ranked_names = ranked_by_score(players_scores.keys(), players_scores)
    num_players = len(ranked_names)
    use_ranked = should_use_ranked_pairing(round_num, ranked_pairing_mode)

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
        singles_matches.append(pair)
        remaining = [p for p in remaining if p not in pair]

    if remaining:
        raise SchedulingError(
            "Internal error: unassigned players remain after singles scheduling."
        )

    assert_schedule_valid(sitting_out, singles_matches, [], ranked_names)
    return _round_result(
        [],
        singles_matches,
        sitting_out,
        ranked_names,
        players_scores,
        round_num,
        ranked_pairing_mode,
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
    competition_mode=COMPETITION_DOUBLES,
    ranked_pairing_mode=RANKED_MODE_AFTER_THREE,
):
    num_players = len(players_scores)
    mode = normalize_competition_mode(competition_mode)
    err = validate_session(num_players, num_courts, mode)
    if err:
        raise SchedulingError(err)

    ranked_mode = normalize_ranked_pairing_mode(ranked_pairing_mode)
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
            ranked_mode,
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
        ranked_mode,
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


def validate_match_score(score_a, score_b, game_to):
    """Return an error message if scores are not a valid completed game, else None."""
    if score_a == 0 and score_b == 0:
        return "Scores cannot both be 0."
    at_cap = sum(1 for score in (score_a, score_b) if score == game_to)
    if at_cap == 0:
        return f"One side must reach {game_to} points to win."
    if at_cap == 2:
        return f"Both sides cannot have {game_to} points."
    return None


def parse_score_value(raw):
    """Parse a single score; return int or None if not a whole number."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return value


def sorted_standings(players_scores):
    return sorted(players_scores.items(), key=lambda x: x[1], reverse=True)


def build_court_plan(competition_mode, num_players, num_courts):
    mode = normalize_competition_mode(competition_mode)
    if mode == COMPETITION_SINGLES:
        sit_out_count = resolve_sit_outs_singles(num_players)
        if sit_out_count is None:
            raise SchedulingError(f"{num_players} players cannot be scheduled.")
        playing = num_players - sit_out_count
        singles_count = min(num_courts, playing // 2)
        courts = [{"type": "singles", "index": i} for i in range(singles_count)]
        return {
            "sit_out_count": sit_out_count,
            "courts": courts,
            "doubles_count": 0,
            "singles_count": singles_count,
        }

    sit_out_count = resolve_sit_outs_doubles(num_players)
    if sit_out_count is None:
        raise SchedulingError(
            f"{num_players} players cannot be scheduled (try adding or removing 1 player)."
        )
    playing = num_players - sit_out_count
    singles_count = 1 if playing % 4 == 2 else 0
    doubles_count = playing // 4
    courts = []
    if singles_count:
        courts.append({"type": "singles", "index": 0})
    for i in range(doubles_count):
        courts.append({"type": "doubles", "index": i})
    return {
        "sit_out_count": sit_out_count,
        "courts": courts,
        "doubles_count": doubles_count,
        "singles_count": singles_count,
    }


def pairings_to_draft(pairings):
    draft = {"doubles": [], "singles": [], "sit_out": ""}
    for side_a, side_b in pairings.get("doubles", []):
        draft["doubles"].append(
            {"a1": side_a[0], "a2": side_a[1], "b1": side_b[0], "b2": side_b[1]}
        )
    for p1, p2 in pairings.get("singles_matches", []):
        draft["singles"].append({"p1": p1, "p2": p2})
    byes = pairings.get("byes", [])
    if byes:
        draft["sit_out"] = byes[0]
    return draft


def parse_manual_pairings(form, court_plan, all_players, round_num, players_scores):
    doubles_matches = []
    singles_matches = []
    sitting_out = []

    if court_plan["sit_out_count"] == 1:
        sit_out = (form.get("sit_out") or "").strip()
        if not sit_out:
            raise SchedulingError("Choose who sits out this round.")
        sitting_out = [sit_out]

    doubles_idx = 0
    singles_idx = 0
    for slot in court_plan["courts"]:
        if slot["type"] == "doubles":
            i = doubles_idx
            doubles_idx += 1
            a1 = (form.get(f"doubles_{i}_a1") or "").strip()
            a2 = (form.get(f"doubles_{i}_a2") or "").strip()
            b1 = (form.get(f"doubles_{i}_b1") or "").strip()
            b2 = (form.get(f"doubles_{i}_b2") or "").strip()
            if not all([a1, a2, b1, b2]):
                raise SchedulingError(f"Court {len(doubles_matches) + len(singles_matches) + 1}: pick all four doubles players.")
            doubles_matches.append(((a1, a2), (b1, b2)))
        else:
            i = singles_idx
            singles_idx += 1
            p1 = (form.get(f"singles_{i}_p1") or "").strip()
            p2 = (form.get(f"singles_{i}_p2") or "").strip()
            if not p1 or not p2:
                raise SchedulingError(f"Court {len(doubles_matches) + len(singles_matches) + 1}: pick both singles players.")
            singles_matches.append((p1, p2))

    validate_manual_pairings(
        doubles_matches, singles_matches, sitting_out, all_players, court_plan
    )
    ranked_names = ranked_by_score(all_players, players_scores)
    return _round_result(
        doubles_matches, singles_matches, sitting_out, ranked_names, players_scores, round_num
    )


def validate_manual_pairings(
    doubles_matches, singles_matches, sitting_out, all_players, court_plan
):
    errors = []
    expected_doubles = court_plan["doubles_count"]
    expected_singles = court_plan["singles_count"]
    if len(doubles_matches) != expected_doubles:
        errors.append(
            f"Expected {expected_doubles} doubles court(s), got {len(doubles_matches)}."
        )
    if len(singles_matches) != expected_singles:
        errors.append(
            f"Expected {expected_singles} singles court(s), got {len(singles_matches)}."
        )
    if len(sitting_out) != court_plan["sit_out_count"]:
        errors.append("Invalid sit-out selection.")

    assigned = {}
    for player in sitting_out:
        if player not in all_players:
            errors.append(f"Unknown sit-out player: {player}.")
        assigned[player] = assigned.get(player, 0) + 1

    for match in singles_matches:
        for player in match:
            if player not in all_players:
                errors.append(f"Unknown player: {player}.")
            assigned[player] = assigned.get(player, 0) + 1

    for side_a, side_b in doubles_matches:
        for player in side_a + side_b:
            if player not in all_players:
                errors.append(f"Unknown player: {player}.")
            assigned[player] = assigned.get(player, 0) + 1

    for player, count in assigned.items():
        if count > 1:
            errors.append(f"{player} is assigned more than once.")

    for player in all_players:
        if assigned.get(player, 0) == 0:
            errors.append(f"{player} is not assigned to a court or sit-out.")

    if errors:
        raise SchedulingError(" ".join(errors))

    try:
        assert_schedule_valid(sitting_out, singles_matches, doubles_matches, all_players)
    except SchedulingError as e:
        raise SchedulingError(str(e)) from e


def record_round_history(
    pairings,
    singles_history,
    partner_history,
    matchup_history,
    singles_matchup_history,
):
    for side_a, side_b in pairings.get("doubles", []):
        record_doubles_match(side_a, side_b, partner_history, matchup_history)
    for match in pairings.get("singles_matches", []):
        record_singles_pair(match, singles_history, singles_matchup_history)


def undo_games_played(games_played, doubles_matches, singles_matches):
    for side_a, side_b in doubles_matches:
        for player in side_a + side_b:
            games_played[player] = max(0, games_played.get(player, 0) - 1)
    for match in singles_matches:
        for player in match:
            games_played[player] = max(0, games_played.get(player, 0) - 1)


def reverse_round_start_effects(
    pairings, players_scores, games_played, sit_out_history, bye_points
):
    _ = players_scores, bye_points
    for player in pairings.get("byes", []):
        sit_out_history[player] = max(0, sit_out_history.get(player, 0) - 1)
    undo_games_played(
        games_played, pairings.get("doubles", []), pairings.get("singles_matches", [])
    )


def commit_manual_round_start(
    pairings, players_scores, games_played, sit_out_history, bye_points
):
    _ = players_scores, bye_points
    for player in pairings.get("byes", []):
        sit_out_history[player] = sit_out_history.get(player, 0) + 1
    record_games_played(
        games_played, pairings["doubles"], pairings["singles_matches"]
    )


def pairings_session_dict(pairings, players_scores, games_played, manual_pairings=False):
    return {
        "doubles": pairings["doubles"],
        "singles_matches": pairings["singles_matches"],
        "byes": pairings["byes"],
        "round_num": pairings["round_num"],
        "rankings": pairings["rankings"],
        "use_ranked_pairing": pairings.get("use_ranked_pairing", False),
        "manual_pairings": manual_pairings,
        "standings": standings_rows(players_scores, games_played),
    }


def apply_sit_out_swap(
    pairings,
    match_kind,
    match_index,
    player_out,
    players_scores,
    games_played,
    sit_out_history,
    bye_points,
):
    _ = players_scores, bye_points
    if len(pairings.get("byes", [])) != 1:
        raise SchedulingError("Swap is only available when one player is sitting out.")
    sit_out = pairings["byes"][0]
    if player_out == sit_out:
        raise SchedulingError("That player is already sitting out.")

    doubles = [((a[0], a[1]), (b[0], b[1])) for a, b in pairings["doubles"]]
    singles = [(p1, p2) for p1, p2 in pairings.get("singles_matches", [])]
    found = False

    if match_kind == "doubles":
        if match_index < 0 or match_index >= len(doubles):
            raise SchedulingError("Invalid court.")
        side_a, side_b = doubles[match_index]
        if player_out in side_a:
            side_a = tuple(sit_out if p == player_out else p for p in side_a)
            found = True
        elif player_out in side_b:
            side_b = tuple(sit_out if p == player_out else p for p in side_b)
            found = True
        if found:
            doubles[match_index] = (side_a, side_b)
    elif match_kind == "singles":
        if match_index < 0 or match_index >= len(singles):
            raise SchedulingError("Invalid court.")
        p1, p2 = singles[match_index]
        if player_out == p1:
            singles[match_index] = (sit_out, p2)
            found = True
        elif player_out == p2:
            singles[match_index] = (p1, sit_out)
            found = True

    if not found:
        raise SchedulingError(f"{player_out} is not on that court.")

    games_played[player_out] = max(0, games_played.get(player_out, 0) - 1)
    games_played[sit_out] = games_played.get(sit_out, 0) + 1
    sit_out_history[player_out] = sit_out_history.get(player_out, 0) + 1
    sit_out_history[sit_out] = max(0, sit_out_history.get(sit_out, 0) - 1)

    updated = dict(pairings)
    updated["doubles"] = doubles
    updated["singles_matches"] = singles
    updated["byes"] = [player_out]
    return updated
