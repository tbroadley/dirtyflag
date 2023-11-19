import berserk

TOKEN = "lip_2QpPax9q1utjJDx9G1t2"
USERNAME = "newwwworld"  # replace with the username you're interested in

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)


def user_won_game(game: dict, username: str) -> bool:
    if not "winner" in game:
        return False
    if (
        game["winner"] == "white"
        and game["players"]["white"]["user"]["name"] == username
    ):
        return True
    if (
        game["winner"] == "black"
        and game["players"]["black"]["user"]["name"] == username
    ):
        return True
    return False


def analysis_showed_user_was_winning(game: dict, username: str) -> bool:
    last_move_analysis = game["analysis"][-1]
    if last_move_analysis is None:
        return False

    last_move_eval_or_mate = (
        last_move_analysis["eval"]
        if "eval" in last_move_analysis
        else last_move_analysis["mate"]
    )

    if (
        game["players"]["white"]["user"]["name"] == username
        and last_move_eval_or_mate > 0
    ):
        return True
    if (
        game["players"]["black"]["user"]["name"] == username
        and last_move_eval_or_mate < 0
    ):
        return True
    return False


def get_dirty_flag_games(username: str):
    games = client.games.export_by_player(
        username,
        as_pgn=False,
        perf_type="rapid,blitz,bullet,ultraBullet",
        analysed=True,
        evals=True,
    )
    dirty_flags = []

    for game in games:
        if game["status"] != "outoftime":
            continue
        if not user_won_game(game, username):
            continue
        if analysis_showed_user_was_winning(game, username):
            continue
        dirty_flags.append(game)

    return dirty_flags


dirty_flag_games = get_dirty_flag_games(USERNAME)
for game in dirty_flag_games:
    game_id = game["id"]
    game_ply_count = len(game["analysis"])
    print(f"https://lichess.org/{game_id}#{game_ply_count}")
