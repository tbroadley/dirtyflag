import berserk
from berserk.models import Game
from stockfish import Stockfish
import sys

TOKEN = sys.argv[1]  # replace with your own token
USERNAME = "newwwworld"  # replace with the username you're interested in

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)


stockfish = Stockfish("./stockfish")


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


def get_rough_evaluation_from_analysis(game: dict) -> int | None:
    if "analysis" not in game:
        return None

    print(f"Checking analysis for game {game['id']}")

    last_move_analysis = game["analysis"][-1]
    if last_move_analysis is None:
        return None

    return (
        last_move_analysis["eval"]
        if "eval" in last_move_analysis
        else last_move_analysis["mate"] * 100_00
    )


def get_rough_evaluation_from_stockfish(game: dict) -> int:
    print(f"Using Stockfish to evaluate game {game['id']}")

    stockfish.set_fen_position(game["lastFen"])
    evaluation = stockfish.get_evaluation()

    return (
        evaluation["value"]
        if evaluation["type"] == "cp"
        else evaluation["value"] * 100_00
    )


def get_dirty_flag_games(username: str):
    # Not using client.games.export_by_player because it doesn't support lastFen
    games = client.games._r.get(
        path=f"https://lichess.org/api/games/user/{username}",
        params={
            "perfType": "rapid,blitz,bullet,ultraBullet",
            "lastFen": True,
            "evals": True,
        },
        fmt=berserk.formats.NDJSON,
        stream=True,
        converter=Game.convert,
    )
    dirty_flags = []

    for game in games:
        if game["status"] != "outoftime":
            continue
        if not user_won_game(game, username):
            continue

        rough_evaluation_centipawns = get_rough_evaluation_from_analysis(game)
        if rough_evaluation_centipawns is None:
            rough_evaluation_centipawns = get_rough_evaluation_from_stockfish(game)

        if (
            game["players"]["white"]["user"]["name"] == username
            and rough_evaluation_centipawns >= -10
        ):
            continue
        if (
            game["players"]["black"]["user"]["name"] == username
            and rough_evaluation_centipawns <= 10
        ):
            continue

        dirty_flags.append(game)

    return dirty_flags


dirty_flag_games = get_dirty_flag_games(USERNAME)
for game in dirty_flag_games:
    game_id = game["id"]
    game_ply_count = len(game["analysis"])
    print(f"https://lichess.org/{game_id}#{game_ply_count}")

stockfish.send_quit_command()
