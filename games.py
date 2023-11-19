import berserk
from berserk.models import Game
from stockfish import Stockfish
import os


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


def get_rough_evaluation_from_stockfish(game: dict, stockfish: Stockfish) -> int:
    print(f"Using Stockfish to evaluate game {game['id']}")

    stockfish.set_fen_position(game["lastFen"])
    evaluation = stockfish.get_evaluation()

    return (
        evaluation["value"]
        if evaluation["type"] == "cp"
        else evaluation["value"] * 100_00
    )


def get_games(client: berserk.Client, username: str) -> list[dict]:
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


def get_dirty_flag_games(games: list[dict], username: str, stockfish: Stockfish):
    dirty_flag_games = []

    for game in games:
        if game["status"] != "outoftime":
            continue
        if not user_won_game(game, username):
            continue

        rough_evaluation_centipawns = get_rough_evaluation_from_analysis(game)
        if rough_evaluation_centipawns is None:
            rough_evaluation_centipawns = get_rough_evaluation_from_stockfish(
                game, stockfish
            )

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


def get_end_of_game_link(game: dict) -> str:
    game_id = game["id"]
    game_ply_count = len(game["moves"].split(" "))
    return f"https://lichess.org/{game_id}#{game_ply_count}"


if __name__ == "__main__":
    lichess_username = "newwwworld"
    lichess_api_token = os.environ["LICHESS_API_TOKEN"]

    berserk_session = berserk.TokenSession(lichess_api_token)
    berserk_client = berserk.Client(session=berserk_session)

    stockfish = Stockfish("./stockfish/src/stockfish")

    games = get_games(berserk_client, lichess_username)
    dirty_flag_games = get_dirty_flag_games(games, lichess_username, stockfish)
    for game in dirty_flag_games:
        print(get_end_of_game_link(game))
