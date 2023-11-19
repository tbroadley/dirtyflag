import os

from flask import Flask, jsonify
from flask import url_for

from dotenv import load_dotenv

load_dotenv()

from authlib.integrations.flask_client import OAuth

import berserk
from stockfish import Stockfish

from games import get_games, get_dirty_flag_games, get_end_of_game_link

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["LICHESS_CLIENT_ID"] = os.getenv("LICHESS_CLIENT_ID")
app.config["LICHESS_AUTHORIZE_URL"] = f"{LICHESS_HOST}/oauth"
app.config["LICHESS_ACCESS_TOKEN_URL"] = f"{LICHESS_HOST}/api/token"

oauth = OAuth(app)
oauth.register("lichess", client_kwargs={"code_challenge_method": "S256"})


stockfish = Stockfish("./stockfish/src/stockfish")


@app.route("/")
def login():
    redirect_uri = url_for("authorize", _external=True)
    """
    If you need to append scopes to your requests, add the `scope=...` named argument
    to the `.authorize_redirect()` method. For admissible values refer to https://lichess.org/api#section/Authentication. 
    Example with scopes for allowing the app to read the user's email address:
    `return oauth.lichess.authorize_redirect(redirect_uri, scope="email:read")`
    """
    return oauth.lichess.authorize_redirect(redirect_uri)


@app.route("/authorize")
def authorize():
    token = oauth.lichess.authorize_access_token()
    bearer = token["access_token"]

    berserk_session = berserk.TokenSession(bearer)
    berserk_client = berserk.Client(session=berserk_session)

    username = berserk_client.account.get()["username"]

    games = get_games(berserk_client, username)
    dirty_flag_games = get_dirty_flag_games(games, username, stockfish)

    response = {
        "count": len(dirty_flag_games),
        "links": [get_end_of_game_link(game) for game in dirty_flag_games],
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run()
