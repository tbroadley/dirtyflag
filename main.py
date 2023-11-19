import berserk
from berserk.models import Game
from stockfish import Stockfish
import os

TOKEN = os.environ["LICHESS_API_TOKEN"]
USERNAME = "newwwworld"  # replace with the username you're interested in

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)


stockfish = Stockfish("./stockfish/src/stockfish")


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


def get_games(username: str) -> list[dict]:
    # Not using client.games.export_by_player because it doesn't support lastFen
    return client.games._r.get(
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


def get_dirty_flag_games(games: list[dict], username: str):
    dirty_flag_games = []

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

        dirty_flag_games.append(game)

    return dirty_flag_games


games = get_games(USERNAME)
dirty_flag_games = get_dirty_flag_games(USERNAME)
for game in dirty_flag_games:
    game_id = game["id"]
    game_ply_count = (
        len(game["analysis"]) if "analysis" in game else (game["moves"] * 2 - 1)
    )
    print(f"https://lichess.org/{game_id}#{game_ply_count}")

stockfish.send_quit_command()
